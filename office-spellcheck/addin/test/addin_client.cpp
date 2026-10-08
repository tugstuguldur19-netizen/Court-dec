// addin_client.cpp - loads the installed add-in the way Office does and
// drives it: CoCreateInstance by ProgID, IDTExtensibility2 through its vtable,
// GetCustomUI through IRibbonExtensibility, and the button callback through
// IDispatch::GetIDsOfNames/Invoke. Office itself is not needed.
//
// Run with OFFICESPELLCHECK_ADDIN_DRYRUN=<file>: the add-in then writes the
// command it would start into that file, and this program checks it.

#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <oleauto.h>
#include <cstdio>
#include <cwchar>
#include <string>

static const IID IID_IDTExtensibility2 = {0xB65AD801, 0xABAF, 0x11D0, {0xBB, 0x8B, 0x00, 0xA0, 0xC9, 0x0F, 0x27, 0x44}};
static const IID IID_IRibbonExtensibility = {0x000C0396, 0x0000, 0x0000, {0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46}};

struct IDTExtensibility2 : public IDispatch {
    virtual HRESULT STDMETHODCALLTYPE OnConnection(IDispatch *app, int mode, IDispatch *addin, SAFEARRAY **custom) = 0;
    virtual HRESULT STDMETHODCALLTYPE OnDisconnection(int mode, SAFEARRAY **custom) = 0;
    virtual HRESULT STDMETHODCALLTYPE OnAddInsUpdate(SAFEARRAY **custom) = 0;
    virtual HRESULT STDMETHODCALLTYPE OnStartupComplete(SAFEARRAY **custom) = 0;
    virtual HRESULT STDMETHODCALLTYPE OnBeginShutdown(SAFEARRAY **custom) = 0;
};

struct IRibbonExtensibility : public IDispatch {
    virtual HRESULT STDMETHODCALLTYPE GetCustomUI(BSTR ribbonId, BSTR *xml) = 0;
};

// An IDispatch with one read-only string property, standing in for Office's
// Application object ("Name") and the ribbon control ("Id").
class FakeDispatch : public IDispatch {
    LONG refs = 1;
    const wchar_t *prop;
    const wchar_t *value;

public:
    FakeDispatch(const wchar_t *p, const wchar_t *v) : prop(p), value(v) {}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **out) override {
        if (riid == IID_IUnknown || riid == IID_IDispatch) {
            *out = static_cast<IDispatch *>(this);
            AddRef();
            return S_OK;
        }
        *out = nullptr;
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { return InterlockedDecrement(&refs); }  // lives on the stack
    HRESULT STDMETHODCALLTYPE GetTypeInfoCount(UINT *n) override { *n = 0; return S_OK; }
    HRESULT STDMETHODCALLTYPE GetTypeInfo(UINT, LCID, ITypeInfo **ti) override { *ti = nullptr; return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE GetIDsOfNames(REFIID, LPOLESTR *names, UINT count, LCID, DISPID *ids) override {
        for (UINT i = 0; i < count; i++) ids[i] = DISPID_UNKNOWN;
        if (count && _wcsicmp(names[0], prop) == 0) {
            ids[0] = 1;
            return S_OK;
        }
        return DISP_E_UNKNOWNNAME;
    }
    HRESULT STDMETHODCALLTYPE Invoke(DISPID id, REFIID, LCID, WORD flags, DISPPARAMS *, VARIANT *result, EXCEPINFO *, UINT *) override {
        if (id != 1 || !(flags & DISPATCH_PROPERTYGET)) return DISP_E_MEMBERNOTFOUND;
        if (result) {
            VariantInit(result);
            result->vt = VT_BSTR;
            result->bstrVal = SysAllocString(value);
        }
        return S_OK;
    }
};

static int failures = 0;

static void check(bool ok, const char *what) {
    printf("  [%s] %s\n", ok ? "ok" : "FAIL", what);
    if (!ok) failures++;
}

static std::wstring read_file(const wchar_t *path) {
    std::wstring out;
    HANDLE h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE) return out;
    char buf[4096];
    DWORD n = 0;
    std::string bytes;
    while (ReadFile(h, buf, sizeof buf, &n, nullptr) && n) bytes.append(buf, n);
    CloseHandle(h);
    int len = MultiByteToWideChar(CP_UTF8, 0, bytes.data(), (int)bytes.size(), nullptr, 0);
    out.resize(len);
    MultiByteToWideChar(CP_UTF8, 0, bytes.data(), (int)bytes.size(), &out[0], len);
    if (!out.empty() && out[0] == 0xFEFF) out.erase(0, 1);
    return out;
}

static void run_host(const wchar_t *appName, const wchar_t *ribbonId, const wchar_t *expectArg, const wchar_t *dryRun) {
    wprintf(L"%ls\n", appName);
    DeleteFileW(dryRun);

    CLSID clsid;
    HRESULT hr = CLSIDFromProgID(L"OfficeSpellcheck.Addin", &clsid);
    check(SUCCEEDED(hr), "ProgID is registered");
    if (FAILED(hr)) return;

    IUnknown *unk = nullptr;
    hr = CoCreateInstance(clsid, nullptr, CLSCTX_INPROC_SERVER, IID_IUnknown, (void **)&unk);
    printf("  CoCreateInstance hr=0x%08lx\n", (unsigned long)hr);
    check(SUCCEEDED(hr), "add-in object is created (in process, through mscoree)");
    if (FAILED(hr)) return;

    IDTExtensibility2 *ext = nullptr;
    check(SUCCEEDED(unk->QueryInterface(IID_IDTExtensibility2, (void **)&ext)), "implements IDTExtensibility2");
    IRibbonExtensibility *ribbon = nullptr;
    check(SUCCEEDED(unk->QueryInterface(IID_IRibbonExtensibility, (void **)&ribbon)), "implements IRibbonExtensibility");
    IDispatch *disp = nullptr;
    check(SUCCEEDED(unk->QueryInterface(IID_IDispatch, (void **)&disp)), "implements IDispatch");
    if (!ext || !ribbon || !disp) return;

    FakeDispatch app(L"Name", appName);
    FakeDispatch addinInst(L"ProgId", L"OfficeSpellcheck.Addin");
    SAFEARRAY *custom = SafeArrayCreateVector(VT_VARIANT, 0, 0);
    check(SUCCEEDED(ext->OnConnection(&app, 1 /* ext_cm_Startup */, &addinInst, &custom)), "OnConnection");
    check(SUCCEEDED(ext->OnAddInsUpdate(&custom)), "OnAddInsUpdate");
    check(SUCCEEDED(ext->OnStartupComplete(&custom)), "OnStartupComplete");

    BSTR id = SysAllocString(ribbonId);
    BSTR xml = nullptr;
    hr = ribbon->GetCustomUI(id, &xml);
    std::wstring ui = xml ? xml : L"";
    check(SUCCEEDED(hr) && ui.find(L"onAction=\"OnCheck\"") != std::wstring::npos, "GetCustomUI returns the button");
    // "Зөв бичиг"
    check(ui.find(L"label=\"Зөв бичиг\"") != std::wstring::npos, "group label is Mongolian");
    check(ui.find(L"idMso=\"TabHome\"") != std::wstring::npos && ui.find(L"idMso=\"TabReview\"") != std::wstring::npos,
          "button on the Home and Review tabs");
    SysFreeString(xml);
    SysFreeString(id);

    BSTR other = SysAllocString(L"Microsoft.Outlook.Explorer");
    xml = nullptr;
    hr = ribbon->GetCustomUI(other, &xml);
    check(SUCCEEDED(hr) && (xml == nullptr || SysStringLen(xml) == 0), "no ribbon for other windows");
    SysFreeString(xml);
    SysFreeString(other);

    // Office calls ribbon callbacks by name through IDispatch.
    LPOLESTR name = const_cast<LPOLESTR>(L"OnCheck");
    DISPID dispid = DISPID_UNKNOWN;
    hr = disp->GetIDsOfNames(IID_NULL, &name, 1, LOCALE_USER_DEFAULT, &dispid);
    check(SUCCEEDED(hr), "OnCheck is reachable through IDispatch");
    if (SUCCEEDED(hr)) {
        FakeDispatch control(L"Id", L"ZuvBichigHomeCheck");
        VARIANT arg;
        VariantInit(&arg);
        arg.vt = VT_DISPATCH;
        arg.pdispVal = &control;
        DISPPARAMS params = {&arg, nullptr, 1, 0};
        VARIANT result;
        VariantInit(&result);
        EXCEPINFO excep = {};
        UINT argErr = 0;
        hr = disp->Invoke(dispid, IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_METHOD, &params, &result, &excep, &argErr);
        printf("  Invoke(OnCheck) hr=0x%08lx\n", (unsigned long)hr);
        check(SUCCEEDED(hr), "clicking the button runs OnCheck");
        VariantClear(&result);

        std::wstring cmd = read_file(dryRun);
        wprintf(L"  command: %ls\n", cmd.c_str());
        size_t bar = cmd.find(L'|');
        std::wstring exe = bar == std::wstring::npos ? L"" : cmd.substr(0, bar);
        std::wstring args = bar == std::wstring::npos ? L"" : cmd.substr(bar + 1);
        check(args == expectArg, "starts the checker for this program");
        check(exe.size() > 21 && _wcsicmp(exe.c_str() + exe.size() - 20, L"OfficeSpellcheck.exe") == 0 &&
                  GetFileAttributesW(exe.c_str()) != INVALID_FILE_ATTRIBUTES,
              "OfficeSpellcheck.exe is next to the add-in");
    }

    check(SUCCEEDED(ext->OnBeginShutdown(&custom)), "OnBeginShutdown");
    check(SUCCEEDED(ext->OnDisconnection(0 /* ext_dm_HostShutdown */, &custom)), "OnDisconnection");
    SafeArrayDestroy(custom);
    disp->Release();
    ribbon->Release();
    ext->Release();
    unk->Release();
}

int wmain() {
    wchar_t dryRun[MAX_PATH] = {};
    if (!GetEnvironmentVariableW(L"OFFICESPELLCHECK_ADDIN_DRYRUN", dryRun, MAX_PATH)) {
        printf("Set OFFICESPELLCHECK_ADDIN_DRYRUN to a file path first.\n");
        return 2;
    }
    printf("client is %d-bit\n", (int)(sizeof(void *) * 8));
    if (FAILED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED))) return 2;  // Office UI threads are STA
    run_host(L"Microsoft Word", L"Microsoft.Word.Document", L"--live word", dryRun);
    run_host(L"Microsoft Excel", L"Microsoft.Excel.Workbook", L"--live excel", dryRun);
    run_host(L"Microsoft PowerPoint", L"Microsoft.PowerPoint.Presentation", L"--live powerpoint", dryRun);
    CoUninitialize();
    printf(failures ? "%d check(s) failed\n" : "all checks passed\n", failures);
    return failures ? 1 : 0;
}

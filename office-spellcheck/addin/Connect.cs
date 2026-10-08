// The add-in object Word, Excel and PowerPoint create at startup. It adds a
// "Зөв бичиг" group to the Home and Review tabs; the button starts
// OfficeSpellcheck.exe (installed next to this DLL) with "--live <app>", so
// the checker opens on the document the user is looking at. If the checker
// is already open, that window takes the request and comes to the front.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

namespace OfficeSpellcheck
{
    [ComVisible(true)]
    [Guid(Connect.ClassId)]
    [ProgId(Connect.ProgIdName)]
    [ClassInterface(ClassInterfaceType.AutoDispatch)]   // Office calls OnCheck through IDispatch
    public class Connect : IDTExtensibility2, IRibbonExtensibility
    {
        public const string ClassId = "AFFFDE13-884F-4B09-9A6A-67F1FE2D4BB3";
        public const string ProgIdName = "OfficeSpellcheck.Addin";

        /// <summary>Tests set this to a file path: the command is written there instead of run.</summary>
        public const string DryRunVariable = "OFFICESPELLCHECK_ADDIN_DRYRUN";

        private string kind = "";   // word | excel | powerpoint

        // ------------------------------------------------------------ IDTExtensibility2

        public void OnConnection(object application, ext_ConnectMode connectMode, object addInInst, ref Array custom)
        {
            kind = KindFromName(GetName(application));
        }

        public void OnDisconnection(ext_DisconnectMode removeMode, ref Array custom) { }
        public void OnAddInsUpdate(ref Array custom) { }
        public void OnStartupComplete(ref Array custom) { }
        public void OnBeginShutdown(ref Array custom) { }

        // ------------------------------------------------------------ ribbon

        public string GetCustomUI(string ribbonId)
        {
            if (kind == "")
                kind = KindFromRibbonId(ribbonId);
            switch (ribbonId)
            {
                case "Microsoft.Word.Document":
                case "Microsoft.Excel.Workbook":
                case "Microsoft.PowerPoint.Presentation":
                    return RibbonXml;
                default:
                    return null;   // other windows (e.g. Outlook items) get nothing
            }
        }

        /// <summary>The button's onAction callback.</summary>
        public void OnCheck(object control)
        {
            try
            {
                Launch(kind == "" ? "word" : kind);
            }
            catch (Exception e)
            {
                // Never let an exception reach Office: it would disable the add-in.
                ShowError("Зөв бичгийн шалгагчийг эхлүүлж чадсангүй.\nCould not start the spellchecker.\n\n" + e.Message);
            }
        }

        internal static readonly string RibbonXml =
            "<customUI xmlns=\"http://schemas.microsoft.com/office/2009/07/customui\">" +
            "<ribbon><tabs>" +
            "<tab idMso=\"TabHome\"><group id=\"ZuvBichigHome\" label=\"Зөв бичиг\">" + Button("ZuvBichigHomeCheck") + "</group></tab>" +
            "<tab idMso=\"TabReview\"><group id=\"ZuvBichigReview\" label=\"Зөв бичиг\">" + Button("ZuvBichigReviewCheck") + "</group></tab>" +
            "</tabs></ribbon></customUI>";

        private static string Button(string id)
        {
            return "<button id=\"" + id + "\" label=\"Алдаа шалгах\" size=\"large\" imageMso=\"Spelling\" onAction=\"OnCheck\"" +
                   " screentip=\"Зөв бичиг шалгах (офлайн)\"" +
                   " supertip=\"Монгол, англи үгийн алдааг интернэтгүйгээр шалгана.&#10;Checks Mongolian and English spelling offline.\"/>";
        }

        // ------------------------------------------------------------ helpers

        internal static string KindFromName(string name)
        {
            name = name ?? "";
            if (name.IndexOf("Excel", StringComparison.OrdinalIgnoreCase) >= 0) return "excel";
            if (name.IndexOf("PowerPoint", StringComparison.OrdinalIgnoreCase) >= 0) return "powerpoint";
            if (name.IndexOf("Word", StringComparison.OrdinalIgnoreCase) >= 0) return "word";
            return "";
        }

        internal static string KindFromRibbonId(string ribbonId)
        {
            return KindFromName(ribbonId);
        }

        private static string GetName(object application)
        {
            try
            {
                return application.GetType().InvokeMember("Name", BindingFlags.GetProperty, null, application, null) as string;
            }
            catch (Exception)
            {
                return null;
            }
        }

        internal static string ExePath()
        {
            string dir = Path.GetDirectoryName(typeof(Connect).Assembly.Location);
            return Path.Combine(dir, "OfficeSpellcheck.exe");
        }

        private static void Launch(string app)
        {
            string exe = ExePath();
            string args = "--live " + app;
            string dryRun = Environment.GetEnvironmentVariable(DryRunVariable);
            if (!string.IsNullOrEmpty(dryRun))
            {
                File.WriteAllText(dryRun, exe + "|" + args);
                return;
            }
            if (!File.Exists(exe))
                throw new FileNotFoundException("OfficeSpellcheck.exe was not found next to the add-in. Please run install.cmd again.", exe);
            var psi = new ProcessStartInfo(exe, args)
            {
                UseShellExecute = false,
                WorkingDirectory = Path.GetDirectoryName(exe),
            };
            Process.Start(psi).Dispose();
        }

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

        private static void ShowError(string text)
        {
            const uint MB_ICONWARNING = 0x30, MB_SETFOREGROUND = 0x10000;
            MessageBoxW(IntPtr.Zero, text, "Зөв бичиг / Office Spellcheck", MB_ICONWARNING | MB_SETFOREGROUND);
        }
    }
}

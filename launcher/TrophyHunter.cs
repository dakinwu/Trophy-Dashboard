// Trophy Hunter Dashboard - Windows .exe launcher.
// A thin wrapper around run.cmd: it locates run.cmd next to the .exe and runs it
// from that folder, so the batch file's own %~dp0 / relative paths keep working.
// Build with launcher\build.ps1 (uses the csc.exe that ships with Windows).
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Trophy Hunter Dashboard")]
[assembly: AssemblyProduct("Trophy Hunter Dashboard")]
[assembly: AssemblyDescription("Starts the Trophy Hunter Dashboard backend and frontend")]

static class Program
{
    [STAThread]
    static int Main()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(dir, "run.cmd");

        if (!File.Exists(script))
        {
            MessageBox.Show(
                "Could not find run.cmd next to this program:\n\n" + dir +
                "\n\nKeep TrophyHunter.exe in the Trophy Hunter Dashboard project folder.",
                "Trophy Hunter Dashboard",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }

        string shell = Environment.GetEnvironmentVariable("ComSpec");
        if (string.IsNullOrEmpty(shell)) shell = "cmd.exe";

        // cmd /c ""<path>"" - the outer quote pair is stripped by cmd, so paths
        // containing spaces survive intact.
        var psi = new ProcessStartInfo(shell, "/c \"\"" + script + "\"\"");
        psi.WorkingDirectory = dir;
        psi.UseShellExecute = false;

        try
        {
            Process.Start(psi);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Failed to start run.cmd:\n\n" + ex.Message,
                "Trophy Hunter Dashboard",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }
        return 0;
    }
}

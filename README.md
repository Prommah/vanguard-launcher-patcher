# EVE Vanguard Linux launcher patcher 

This script patches two files in the EVE launcher to fix launching Vanguard on
Linux. This will probably need to be reapplied if the launcher is updated and may
not work for new launcher versions without some changes.

Just run the `vanguard-launcher-patcher.py` Python script and pass it the path to
your EVE launcher when prompted.

Only tested with launcher version `1.11.2`.

If anything goes wrong, the script should restore the original files. If not,
they should be in the launcher directory: `eve-online.exe.bak` and `resources/app.asar.bak`. 

### Why is this necessary?

The launcher currently wraps every argument in double quotes in addition to the
values passed in the arguments.
For example: `"-GatewayAddress="gateway.production.services.evevanguardtech.com:443"" "-ClientID=eveLauncherTQ"  ...`.

As far as I can tell, this is unnecessary on both Windows and Linux, and causes
issues on Linux. On Linux, a shell would strip out these excessive quotes but the
quotes are kept due to how the game process is started by the launcher, and the
game process doesn't seem to be able to parse them when that happens.

### How does this fix it?

The launcher is an Electron app that calls out to a native module to start
processes. The `startProcess` function in this module's API has a `useQuotes`
option that is currently unused by the launcher. This script sets this option
 to `false`.

This script patches `app.asar` which is an [archive file](https://github.com/electron/asar)
containing the JavaScript of the Electron app. The `eve-online.exe` launcher
executable then has to be patched with the new integrity hash.

Credit to [this article](https://infosecwriteups.com/electron-js-asar-integrity-bypass-431ac4269ed5)
for information on exactly what's required for everything here.

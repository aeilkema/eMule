# /goal — Preview 2 Complete Settings & Theme Coverage

Status: **implemented on `goal-1-5`, local build/runtime proof pending**.

Last user-confirmed build-proven basis before this tranche: `b0f207535b35bdd229fdce4e8ce9fcf6a8ae747b`.

## Goal

Preview 2 must expose the complete configuration surface of upstream eMule through one Settings entry point and must not show large system-white surfaces in Dark mode during normal primary-workspace use.

## SETTINGS-01 — Single complete Settings entry

The modern Settings workspace remains the primary entry from the Preview 2 sidebar.

### Native eMule Next categories

1. Appearance
2. Peer knowledge
3. Intelligence
4. Advanced

These remain directly editable in the modern page and keep existing Preview 2 bounded/default behavior.

### Complete upstream eMule Preferences coverage

The Settings navigation now also exposes every production page registered by `CPreferencesDlg`:

1. General
2. Display
3. Connection
4. Proxy
5. Server
6. Directories
7. Files
8. Notifications
9. Statistics
10. IRC
11. Messages
12. Security
13. Scheduler
14. Web Server
15. Tweaks

Debug remains conditional to debug builds and is not a production Preview 2 Settings requirement.

For upstream pages Preview 2 deliberately does **not** duplicate hundreds of values into a second settings model. Selecting an original category provides a direct action to the exact original `CPreferencesDlg` property page through `CemuleDlg::ShowPreferences(pageId)`. The original property page, validation, apply/save behavior and `thePrefs` storage remain authoritative.

The materializer derives each page resource ID from its existing `PPg*.h` declaration at activation time. This avoids maintaining a second hardcoded resource-ID table.

### Settings UX requirements

- all 19 production categories (4 Next + 15 original) are represented;
- original categories are clearly labeled as original eMule preference pages;
- direct page routing opens the selected category, not merely the generic Preferences dialog;
- the redundant generic `Classic eMule settings...` button is hidden from normal category use;
- original pages retain their existing Apply/OK semantics;
- Settings navigation uses a vertical scrollbar for high DPI/small windows;
- Next Settings layout contains no incompatible unqualified `min/max` helpers.

## UI-06 — Complete theme coverage

### Primary legacy workspace routing

Whenever `CemuleDlg::SetActiveDialog` shows a legacy primary workspace, Preview 2 reapplies the active theme recursively to its window tree. This covers the normal navigation paths for:

- Transfers
- Shared Files
- Messages
- Servers
- Kad
- Statistics
- IRC
- Search host and other legacy child views shown through the main shell

This is an additive presentation hook only; it does not alter protocol or workspace logic.

### Original Preferences

After the original `CPreferencesDlg` and all property pages are initialized, Preview 2 applies the active theme recursively to the complete Preferences tree. All page logic remains upstream/authoritative.

### Messages / Chat specialist coverage

Chat requires extra treatment because rich-edit log surfaces and edit/static controls do not reliably become dark through the generic Windows theme hook alone.

Preview 2 therefore adds:

- a themed Chat window brush for static/edit/dialog controls;
- modern list styling for Friends;
- Explorer theme hooks for chat tabs, input, buttons and toolbar;
- dark/light background and default text colors for newly created `CHTRichEditCtrl` chat logs;
- `CChatSelector::ApplyPreview2Theme()` to update already-open chat sessions when the theme changes or the workspace is revisited.

## Gates

`verify-preview2-settings-theme.py` must verify:

- the production page list in `PreferencesDlg.cpp` still matches the 15 pages represented in Preview 2;
- all 15 navigation labels exist;
- at least 15 direct `ShowPreferences(IDD_...)` page routes exist;
- original-page UX controls exist;
- legacy workspaces are themed from the central activation route;
- original Preferences is recursively themed;
- Chat window, Friends list, tabs and rich-edit session surfaces have explicit theme coverage.

`verify-preview2-activation-chain.py` and `verify-preview2-release.ps1` require the complete Settings, Settings hardening, legacy theme routing, Chat theme coverage and final Settings/theme gate in the late Preview 2 product chain.

## Runtime acceptance still required

A successful compile does not complete UI-06. Runtime tests must still check:

- Settings shows all 19 production categories;
- each of the 15 original categories opens the intended upstream page;
- Apply/OK persist original settings exactly as before;
- Settings remains usable at DPI 100/125/150/175/200%;
- Dark mode: Messages/Chat has no large white surfaces, including existing and newly opened chat sessions;
- Dark mode: Servers, Kad, Shared Files, Statistics and IRC do not fall back to large system-white surfaces after navigation;
- Light and System mode remain readable;
- changing theme and revisiting workspaces refreshes the presentation without restarting;
- no protocol/network/database behavior changes are introduced by theming.

## Release discipline

Build success, UI/theme runtime success, and live protocol/runtime success remain separate evidence classes. `goal-1-5` is not merged into `develop` without explicit user permission.

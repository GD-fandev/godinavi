# Modal conventions

GodiNavi modals are owned utility windows displayed above the Godius client. They must remain interactive without preventing the user from switching to another Windows application.

## Focus and input rules

- Open and reactivate shared modals through `modal_window.activate_modal()`.
- Do not call `focus_force()` from a modal.
- Do not call `SetForegroundWindow()` merely to open, refresh, close, or reposition a modal.
- A user action that explicitly requests returning to Godius may call `focus_native_window()`, but only from that action's direct button callback. Never call it from a timer, render loop, OCR callback, alarm completion, or modal lifecycle callback.
- Release a modal-owned Tk grab when the modal is destroyed. Nested dialogs may restore their parent grab explicitly, but must not leave a global grab behind.
- Showing or repositioning an owned overlay while another application is foreground must not raise the Godius owner group.

These rules apply to every modal and overlay, including the clock, stopwatch, alarm, tutorial, dictionary, party, update, and settings interfaces.

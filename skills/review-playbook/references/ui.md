# UI and app checklist

Look at the rendered result whenever possible. Compiling is not the same as looking right.

## All interfaces

- Every state exists and was seen: loading, empty, error, success, offline, partial data.
- Layout survives long text, missing images, small and large screens, large text size, dark mode and rotation.
- Buttons cannot be double-submitted. Slow actions show progress and fail gracefully.
- Forms validate, show clear messages next to the field, and keep what the user typed after an error.
- Text is not hard-coded if the app is translated; layouts survive longer strings and right-to-left languages.
- Controls have accessible names, enough colour contrast, a visible focus state and a usable tap size (about 44 by 44 points).
- Everything works with a keyboard alone, in a sensible order.
- Navigation works both ways: back, deep links, returning from the background, and state restored after the app is killed or the page reloads.

## Web

- No horizontal scrolling on a narrow phone screen (about 375 pixels wide).
- The browser console shows no errors or warnings caused by this change.
- Images have useful `alt` text, a set size or aspect ratio so the page does not jump, and a sensible file size.
- Links that open a new tab use `rel="noopener"`.
- Pages have a meaningful `<title>`, one `<h1>`, and headings in order.
- Anything stored in `localStorage` or cookies can be missing or blocked without breaking the page.

## SwiftUI and iOS

- UI state changes on the main actor; no long work on the main thread.
- Correct ownership: `@State` / `@StateObject` for what the view owns, `@Binding` / `@ObservedObject` / the environment for what it is given. A view does not recreate its model on every redraw.
- No retain cycles in closures and tasks. Tasks are cancelled when the view disappears (`.task` handles this; a manual `Task {}` does not).
- No force unwrap (`!`), `try!` or forced cast on anything that can really be nil or fail.
- `List` and `ForEach` use stable, unique ids, never the array index for mutable data.
- No heavy work inside `body`.
- Permission prompts have usage descriptions in `Info.plist` and a path for when the user declines.
- Secrets and tokens are in the Keychain, not `UserDefaults` or source code.
- Checked on a small and a large device, in light and dark mode, and with a large Dynamic Type size.

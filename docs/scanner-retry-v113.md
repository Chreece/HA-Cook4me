# Scanner retry and inline expiry — v113

Panel build: `2026.9.17.17`.

A failed or unknown barcode lookup exposes a Restart icon immediately to the
left of Apply, inside the camera frame. Restart clears the failed draft and
starts barcode recognition again, including another attempt at the same code.
It preserves the selected storage place and the live camera stream. A successful
product remains locked until Apply; an uncertain save retains its immutable
request and must use Apply to retry saving rather than discarding that request.

After barcode or AI product recognition, an editable expiry-date field appears
immediately below the amount controls. It uses the existing UI-language label
and native date input. Edits, including clearing the date, update the same draft
and full editor; manual editor changes and date-label scans update the inline
field. Apply adds every selected package with that reviewed expiry date. The
next product starts with an empty expiry field. Stock remains additive.

Validation uses the actual bundled panel with a synthetic camera and mocked
providers. It checks lookup failures, unknown codes, same-code retries without
camera interruption, date editing and clearing, label/manual synchronization,
English/Greek labels, 360/390/1280 px layouts, three packages sharing the date,
and immutable retries after an uncertain save. The existing product-review and
package-editing browser checks also run against v113. Installer success and
rollback checks use a simulated host; no live phone or HA host was available.

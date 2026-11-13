# System image update path

R22 reserves three app slots: a factory recovery image and two OTA system images. The update component always requests ESP-IDF's next OTA partition and rejects the factory partition as a target.

The transport that receives image bytes is intentionally separate. A future USB service can:

1. Call `slim4_system_update_begin(total_image_bytes)`.
2. Feed ordered payload chunks to `slim4_system_update_write(data, length)`.
3. Call `slim4_system_update_finish()` after the complete image is sent. ESP-IDF validates the image and selects that OTA slot for the next boot.
4. Call `slim4_system_update_abort()` if the transfer is canceled before finish.
5. Reboot only after the transport has acknowledged the selected image.

Only one update writer may run at a time. Writes beyond the declared image size are rejected. Finishing before all declared bytes arrive is rejected and leaves the update session open so the caller can send the remaining data or abort.

With rollback enabled, the candidate starts in `PENDING_VERIFY`. The app confirms it only after the control input API, display framebuffer, and audio worker initialize. If a software self-test fails, it requests rollback. This check cannot prove that a physical panel shows the correct image or that speakers sound correct.

The update path currently has no USB receiver, image signature verification, secure boot provisioning, encryption policy, or launcher/game-package installer. Until authentication is added, the transport must not accept firmware bytes from an untrusted source.

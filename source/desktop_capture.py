"""DXGI full-output capture followed by client cropping; no GDI fallback."""
from PIL import Image


def intersect(a, b):
    box = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    return box if box[2] > box[0] and box[3] > box[1] else None


class DesktopCapture:
    def __init__(self, module=None):
        if module is None:
            import dxcam as module
        self.module = module
        self.cameras = {}

    def capture_client(self, rect):
        left, top, right, bottom = rect
        if right <= left or bottom <= top:
            raise ValueError("Invalid client rectangle")
        client = Image.new("RGB", (right-left, bottom-top))
        covered = 0
        outputs = []
        # Installed DXcam exposes desktop coordinates through its output descriptors.
        # Keep this version-specific access isolated here; never assume primary-monitor origin.
        for device_id, device_outputs in enumerate(self.module.__dict__["__factory"].outputs):
            for output_id, output in enumerate(device_outputs):
                output.update_desc()
                if not output.attached_to_desktop:
                    continue
                r = output.desc.DesktopCoordinates
                desktop = (r.left, r.top, r.right, r.bottom)
                overlap = intersect(rect, desktop)
                if overlap is None:
                    continue
                key = (device_id, output_id)
                camera = self.cameras.get(key)
                if camera is None:
                    camera = self.module.create(device_idx=device_id, output_idx=output_id,
                        output_color="RGB", backend="dxgi", processor_backend="numpy")
                    self.cameras[key] = camera
                # Deliberately NO region argument. Crop only after full output acquisition.
                frame = camera.grab(new_frame_only=False)
                if frame is None:
                    raise RuntimeError("Desktop Duplication 프레임 없음 · 다음 캡처에서 재시도")
                if (frame.shape[1], frame.shape[0]) != (r.right-r.left, r.bottom-r.top):
                    raise RuntimeError("모니터 크기 변경 감지 · 프레임 폐기")
                full = Image.fromarray(frame, mode="RGB")
                x1, y1, x2, y2 = overlap
                client.paste(full.crop((x1-r.left, y1-r.top, x2-r.left, y2-r.top)), (x1-left, y1-top))
                covered += (x2-x1)*(y2-y1)
                outputs.append({"device": device_id, "output": output_id, "desktop_rect": desktop,
                                "full_frame_size": full.size})
        if covered != (right-left)*(bottom-top):
            raise RuntimeError("게임 영역이 모니터 밖에 있어 전체 캡처 불가")
        return client, {"backend": "DXGI Desktop Duplication", "strategy": "full_output_then_client_crop",
                        "outputs": outputs}

    def close(self):
        for camera in self.cameras.values():
            try:
                camera.release()
            except Exception:
                pass
        self.cameras.clear()

"""Original Windows.Media.Ocr backend kept for immediate rollback."""

import asyncio
import io
import threading

from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream


class WindowsOcrBackend:
    LANGUAGE_TAGS = {"ko": "ko-KR", "ja": "ja-JP", "en": "en-US"}

    def __init__(self):
        self.local = threading.local()

    def recognize_multilingual(self, name_image, coordinate_image):
        return asyncio.run(self._recognize_multilingual(name_image, coordinate_image))

    def recognize_map_language(self, name_image, coordinate_image, language_key):
        return asyncio.run(self._recognize_map_language(name_image, coordinate_image, language_key))

    async def _recognize_map_language(self, name_image, coordinate_image, language_key):
        language_tag = self.LANGUAGE_TAGS[language_key]
        return (
            {language_key: await self._recognize(name_image, language_tag)},
            await self._recognize(coordinate_image, "en-US"),
        )

    def recognize_coordinates(self, coordinate_image):
        return asyncio.run(self._recognize(coordinate_image, "en-US"))

    async def _recognize_multilingual(self, name_image, coordinate_image):
        name_results = {}
        for language_key, language_tag in self.LANGUAGE_TAGS.items():
            name_results[language_key] = await self._recognize(name_image, language_tag)
        coordinate_text = await self._recognize(coordinate_image, "en-US")
        return name_results, coordinate_text

    def get_engine(self, language_tag):
        engines = getattr(self.local, "engines", None)
        if engines is None:
            engines = {}
            self.local.engines = engines
        if language_tag not in engines:
            language = Language(language_tag)
            engines[language_tag] = (
                OcrEngine.try_create_from_language(language)
                if OcrEngine.is_language_supported(language)
                else None
            )
        return engines[language_tag]

    async def _recognize(self, image, language_tag):
        engine = self.get_engine(language_tag)
        if engine is None:
            return ""

        memory = io.BytesIO()
        image.save(memory, format="PNG")
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream.get_output_stream_at(0))
        writer.write_bytes(memory.getvalue())
        await writer.store_async()
        writer.detach_stream()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        return result.text.strip()

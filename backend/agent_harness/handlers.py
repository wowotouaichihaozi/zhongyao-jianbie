"""Handler-key registry for manifest-declared XiaoZhi skills."""

from __future__ import annotations

from typing import Any, Callable

try:
    from agent_manifest import DEFAULT_AGENT_MANIFEST, AgentManifest
except ImportError:  # pragma: no cover
    from ..agent_manifest import DEFAULT_AGENT_MANIFEST, AgentManifest


ProgressCallback = Callable[[dict[str, Any]], None]
RuntimeHandler = Callable[[dict[str, Any], ProgressCallback], dict[str, Any]]
HandlerAdapter = Callable[[RuntimeHandler, dict[str, Any], ProgressCallback], dict[str, Any]]


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, HandlerAdapter] = {}

    def register(self, handler_key: str, adapter: HandlerAdapter) -> None:
        key = str(handler_key or "").strip()
        if not key:
            raise ValueError("handler key is required")
        if key in self._handlers:
            raise ValueError(f"duplicate handler key: {key}")
        if not callable(adapter):
            raise TypeError(f"handler adapter must be callable: {key}")
        self._handlers[key] = adapter

    def resolve(self, handler_key: str) -> HandlerAdapter:
        key = str(handler_key or "").strip()
        if key not in self._handlers:
            raise KeyError(f"handler is not registered: {key}")
        return self._handlers[key]

    def invoke(
        self,
        handler_key: str,
        runtime_handler: RuntimeHandler,
        arguments: dict[str, Any],
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        return self.resolve(handler_key)(runtime_handler, arguments, progress)

    def validate_manifest(self, manifest: AgentManifest) -> None:
        missing = sorted(
            {
                str(skill.get("handlerKey") or "")
                for skill in manifest.skills
                if str(skill.get("handlerKey") or "") not in self._handlers
            }
        )
        if missing:
            raise ValueError(f"manifest references missing handlers: {missing}")

    def status(self) -> dict[str, Any]:
        return {
            "handlerCount": len(self._handlers),
            "handlerKeys": sorted(self._handlers),
        }


def _invoke_runtime_handler(
    runtime_handler: RuntimeHandler,
    arguments: dict[str, Any],
    progress: ProgressCallback,
) -> dict[str, Any]:
    if not callable(runtime_handler):
        raise RuntimeError("manifest handler has no bound platform implementation")
    return runtime_handler(arguments, progress)


DEFAULT_HANDLER_REGISTRY = HandlerRegistry()
for _handler_key in (
    "learning_background.collect",
    "learning_profile.refresh",
    "learning_profile.manage",
    "learning_path.generate",
    "learning_path.stage_detail",
    "resource.package.generate",
    "resource.question_bank.generate",
    "resource.ppt.generate",
    "resource.document.generate",
    "resource.mindmap.generate",
    "resource.video.search",
    "resource.generated_video.generate",
    "resource.animation.generate",
    "mcu.experiment.recommend",
    "interview.session.run",
    "learning.tutor.answer",
    "learning.effect.evaluate",
    "learning_feedback.submit",
    "knowledge_base.manage",
):
    DEFAULT_HANDLER_REGISTRY.register(_handler_key, _invoke_runtime_handler)

DEFAULT_HANDLER_REGISTRY.validate_manifest(DEFAULT_AGENT_MANIFEST)

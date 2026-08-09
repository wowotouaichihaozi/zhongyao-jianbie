"""Non-secret defaults for the backend service.

Runtime credentials must be supplied through environment variables or
``backend/.env``. Keeping secrets out of this module prevents them from being
bundled into source archives or exposed by source inspection.
"""

from typing import Dict


DEFAULT_SETTINGS: Dict[str, str] = {
    # ── Server Configuration ────────────────────────────────────────────────
    "PORT": "3000",
    "FRONTEND_ORIGIN": "https://lzhan.xyz,https://www.lzhan.xyz,https://localhost,capacitor://localhost,http://120.26.3.150",

    # ── SMTP Email Configuration ────────────────────────────────────────────
    "SMTP_HOST": "",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": "",
    "SMTP_PASSWORD": "",
    "SMTP_FROM_EMAIL": "",
    "SMTP_FROM_NAME": "飞声望影",
    "SMTP_USE_SSL": "true",
    "SMTP_USE_TLS": "false",

    # ── Coze AI Configuration ───────────────────────────────────────────────
    "COZE_API_BASE_URL": "https://api.coze.cn/v3/chat",
    "COZE_API_TOKEN": "",
    "COZE_BOT_ID": "7629982400718241832",
    "COZE_USER_ID": "123456789",

    # ── Coze Workflow Configuration ─────────────────────────────────────────
    "COZE_WORKFLOW_API_URL": "https://api.coze.cn/v1/workflows/chat",
    "COZE_WORKFLOW_TOKEN": "",
    "COZE_WORKFLOW_ID": "7630821412551032832",

    # ── Remote Upload Configuration (SSH) ───────────────────────────────────
    "REMOTE_UPLOAD_HOST": "120.26.3.150",
    "REMOTE_UPLOAD_PORT": "22",
    "REMOTE_UPLOAD_USERNAME": "root",
    "REMOTE_UPLOAD_PASSWORD": "",
    "REMOTE_UPLOAD_DIR": "/var/www/neuroguard-media/feishengwangying",
    "REMOTE_UPLOAD_BASE_URL": "https://lzhan.xyz/neuroguard-media/feishengwangying",

    # ── OSS Storage Configuration ───────────────────────────────────────────
    "UPLOAD_STORAGE_PROVIDER": "oss",
    "OSS_ACCESS_KEY_ID": "",
    "OSS_ACCESS_KEY_SECRET": "",
    "OSS_ENDPOINT": "https://oss-cn-shanghai.aliyuncs.com",
    "OSS_BUCKET": "feishengwangyin",
    "OSS_OBJECT_PREFIX": "feishengwangying",
    "OSS_PUBLIC_BASE_URL": "https://feishengwangyin.oss-cn-shanghai.aliyuncs.com/feishengwangying",
    "OSS_DEDUP_ENABLED": "true",

    # ── Visual Crop Configuration ───────────────────────────────────────────
    "VISUAL_CROP_ENABLED": "true",
    "VISUAL_CROP_YOLO_MODEL": "yolov8n.pt",
    "VISUAL_CROP_YOLO_MODELS": "",
    "VISUAL_CROP_CONFIDENCE": "0.25",
    "VISUAL_CROP_MARGIN": "0.12",

    # ── Avatar (讯飞数字人) Configuration ──────────────────────────────────
    "AVATAR_APP_ID": "",
    "AVATAR_API_KEY": "",
    "AVATAR_API_SECRET": "",
    "AVATAR_SCENE_ID": "",
    "AVATAR_SCENE_VERSION": "",
    "AVATAR_ID": "",
    "AVATAR_VCN": "x4_yezi",
    "AVATAR_SERVER_URL": "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact",
    "AVATAR_SIGN_HOST": "avatar.cn-huadong-1.xf-yun.com",
    "AVATAR_SIGN_PATH": "/v1/interact",
    "AVATAR_STREAM_PROTOCOL": "xrtc",
    "AVATAR_STREAM_FPS": "25",
    "AVATAR_STREAM_BITRATE": "1000000",
    "AVATAR_STREAM_ALPHA": "1",
    "AVATAR_WIDTH": "720",
    "AVATAR_HEIGHT": "1280",
    "AVATAR_AUDIO_FORMAT": "1",
    "AVATAR_TTS_SPEED": "50",
    "AVATAR_TTS_PITCH": "50",
    "AVATAR_TTS_VOLUME": "100",
    "AVATAR_LEGACY_ENABLED": "true",
    "AVATAR_LEGACY_HOST": "vms.cn-huadong-1.xf-yun.com",
    "AVATAR_LEGACY_ID": "",
    "AVATAR_LEGACY_VCN": "x3_yezi",
    "AVATAR_LEGACY_WIDTH": "1280",
    "AVATAR_LEGACY_HEIGHT": "720",

    # ── Anthropic / Mimo AI Configuration ───────────────────────────────────
    "ANTHROPIC_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "",
    "ANTHROPIC_MODEL": "xsparkx2agent",
    "OPENAI_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
    "LLM_PROTOCOL": "auto",
    "LLM_CONTEXT_WINDOW": "262144",
    "VISION_LLM_MODEL": "xopkimik26",
    "VISION_LLM_CONTEXT_WINDOW": "262144",
    "VISION_LLM_TIMEOUT": "120",
    "VISION_LLM_MAX_TOKENS": "1800",
    "AGENT_RUNTIME_ALLOWED_HOSTS": "maas-coding-api.cn-huabei-1.xf-yun.com,localhost,127.0.0.1",
    "PPT_H5_LLM_TIMEOUT": "10",
    "PPT_H5_LLM_RETRIES": "3",
    "OHMYPPT_API_URL": "http://127.0.0.1:8765/api",
    "OHMYPPT_REQUEST_TIMEOUT": "600",
    "OHMYPPT_INTERNAL_TOKEN": "",

    # Hermes Agent Runtime Configuration
    "HERMES_AGENT_API_URL": "",
    "HERMES_AGENT_BASE_URL": "",
    "HERMES_AGENT_AUTH_TOKEN": "",
    "HERMES_AGENT_MODEL": "",
    "HERMES_XIAOZHI_AGENT_ID": "xiaozhi-companion-agent",
    "HERMES_XIAOZHI_AGENT_NAME": "嵌小智陪伴式助手",

    # ── Interview Timeout Configuration ─────────────────────────────────────
    "MIMO_INTERVIEW_TIMEOUT": "60",
    "ANTHROPIC_INTERVIEW_TIMEOUT": "60",

    # ── MySQL Configuration (Optional) ──────────────────────────────────────
    "MYSQL_HOST": "",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "",
    "MYSQL_PASSWORD": "",
    "MYSQL_DATABASE": "",
    "MYSQL_SSH_TUNNEL_ENABLED": "false",
    "MYSQL_SSH_HOST": "",
    "MYSQL_SSH_PORT": "22",
    "MYSQL_SSH_USERNAME": "",
    "MYSQL_SSH_PASSWORD": "",
    "MYSQL_SSH_REMOTE_HOST": "127.0.0.1",
    "MYSQL_SSH_REMOTE_PORT": "3306",

    # ── Admin Configuration ─────────────────────────────────────────────────
    "ADMIN_USERNAME": "admin123",
    "ADMIN_PASSWORD": "admin123",

    # ── Amap (高德地图) Configuration ──────────────────────────────────────
    "VITE_AMAP_KEY": "",
    "VITE_AMAP_SECRET": "",
}


def setting_default(name: str, fallback: str = "") -> str:
    return DEFAULT_SETTINGS.get(name, fallback)

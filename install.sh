#!/usr/bin/env bash
# ============================================================
# Hermes Skills 一键安装器 / One-click Installer
# 把仓库里所有技能装到目标目录，并创建全局命令（可选）
#
# 用法 / Usage:
#   ./install.sh                          # 装到 ~/.hermes/skills/utilities/（Hermes 默认）
#   ./install.sh ~/my-skills              # 装到自定义目录（任意 Agent / 项目）
#
# 安装后可用（核心技能的全局命令）:
#   deai-demo   去 AI 味免key演示（无需任何配置，30秒看效果）
#   deai-writer 去 AI 味 / 风格克隆 / 变体 / 语气 / 评分（需 LLM key）
#   vtt         视频转文字（抖音链接元数据 / 本地视频转写）
#   dococr      文档 OCR（PDF/扫描件提取文字）
#   memcheck    Agent 记忆健康检查
#   memory-graph 长文记忆图谱
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$REPO_DIR/skills"
TARGET="${1:-$HOME/.hermes/skills/utilities}"
BIN_DIR="$HOME/.local/bin"

echo "📦 Hermes Skills 安装器"
echo "   源目录: $SKILLS_SRC"
echo "   目标目录: $TARGET"
echo ""

# ── 1. 复制技能目录 ──
mkdir -p "$TARGET"
echo "🔄 复制技能..."
for d in "$SKILLS_SRC"/*/; do
    name="$(basename "$d")"
    # 跳过安装器自己的产物/隐藏目录
    [ "$name" = "scripts" ] && continue
    rm -rf "$TARGET/$name"
    cp -R "$d" "$TARGET/$name"
    echo "  ✅ $name"
done

# ── 2. 建全局命令（~/.local/bin，已在 PATH 则直接可用）──
echo ""
echo "🔄 创建全局命令到 $BIN_DIR ..."
mkdir -p "$BIN_DIR"

link_script() { # $1=脚本路径 $2=命令名
    chmod +x "$1"
    ln -sf "$1" "$BIN_DIR/$2"
}

DEAI_DIR="$TARGET/de-ai-writer/scripts"
link_script "$DEAI_DIR/demo.py"    deai-demo
link_script "$DEAI_DIR/deai.py"    deai-writer
link_script "$DEAI_DIR/writer.py"  writer

[ -f "$TARGET/video-to-text/scripts/vtt.py" ] && link_script "$TARGET/video-to-text/scripts/vtt.py" vtt
[ -f "$TARGET/video-to-text/scripts/vtt.py" ] && link_script "$TARGET/video-to-text/scripts/vtt.py" v2t
[ -f "$TARGET/doc-ocr/scripts/dococr.py" ] && link_script "$TARGET/doc-ocr/scripts/dococr.py" dococr
[ -f "$TARGET/memory-manager/scripts/memcheck.py" ] && link_script "$TARGET/memory-manager/scripts/memcheck.py" memcheck
[ -f "$TARGET/memory-graph/scripts/memory_graph.py" ] && link_script "$TARGET/memory-graph/scripts/memory_graph.py" memory-graph

# ── 3. PATH 提示 ──
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo ""
       echo "⚠️  $BIN_DIR 不在 PATH，把它加进 shell 配置（~/.zshrc）:"
       echo "   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
       ;;
esac

echo ""
echo "🎉 安装完成！试试:"
echo "   deai-demo                        # 免key演示：去 AI 味 30 秒看效果"
echo "   deai-demo -t \"你的AI味文本\"       # 处理你自己的文本"
echo "   echo '文本' | deai-writer -      # LLM 深度改写（配 LLM_API_KEY 后）"
echo ""
echo "💡 想装成 Hermes 官方技能（带 description 触发）:"
echo "   hermes skills install jiawood2006/hermes-skills/skills/de-ai-writer"

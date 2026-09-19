/* ============================================
   公共前端工具：调色板 / fetch 封装 / 提示 / 确认 / 图表基础配置
   ============================================ */

/* ---------- 调色板（与设计规范同源，已通过 CVD 校验脚本验证） ----------
   类别色槽（固定顺序，颜色跟随实体而非排名；散点/全组合场景最多用前 3 槽） */
const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];
/* 序贯蓝 ramp 的 250-650 步：用于有序类别（成绩分段：分数越高颜色越深） */
const SEQ_BLUE = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'];
/* 墨色 / 表面 / 网格线 */
const INK = {
  primary: '#0b0b0b',
  secondary: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  surface: '#fcfcfb',
  border: 'rgba(11,11,11,0.10)',
};

/* ---------- fetch 封装 ---------- */
async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (resp.status === 401) {
    location.href = '/login';
    throw new Error('未登录');
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    // FastAPI 422 的 detail 是数组；其余为字符串（可能是 DB 触发器的中文报错，原样展示）
    const msg = Array.isArray(data.detail)
      ? data.detail.map((d) => d.msg).join('；')
      : (data.detail || '操作失败');
    throw new Error(msg);
  }
  return data;
}

/* ---------- Toast 提示 ---------- */
function toast(msg, type = 'success') {
  const root = document.getElementById('toast-root');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icon = document.createElement('span');
  icon.className = 'icon';
  icon.textContent = type === 'error' ? '✕' : '✓';
  const text = document.createElement('span');
  text.textContent = msg;
  el.append(icon, text);
  root.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ---------- 删除确认（含级联后果文案） ---------- */
function confirmDelete(message) {
  return window.confirm(message);
}

/* ---------- HTML 转义（JS 拼接用户数据进 DOM 前必须过一遍） ---------- */
function escapeHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/* ---------- Modal ---------- */
function openModal(id) {
  document.getElementById(id).style.display = 'flex';
}
function closeModal(id) {
  document.getElementById(id).style.display = 'none';
}

/* ---------- ECharts 基础配置（所有图共用：浅色表面 / 墨色文字 / 细网格线） ---------- */
function baseChartOption() {
  return {
    textStyle: {
      fontFamily: 'system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif',
      color: INK.secondary,
    },
    tooltip: {
      backgroundColor: INK.surface,
      borderColor: INK.border,
      borderWidth: 1,
      textStyle: { color: INK.primary, fontSize: 12 },
      padding: [8, 10],
    },
  };
}

/* 类别轴 / 数值轴样式：细网格线、弱化轴线（图表装饰一律用墨色 token，不用系列色） */
function catAxisStyle() {
  return {
    axisLine: { lineStyle: { color: INK.axis } },
    axisTick: { show: false },
    axisLabel: { color: INK.secondary, fontSize: 12 },
    splitLine: { show: false },
  };
}
function valAxisStyle() {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: INK.muted, fontSize: 11 },
    splitLine: { lineStyle: { color: INK.grid } },
  };
}

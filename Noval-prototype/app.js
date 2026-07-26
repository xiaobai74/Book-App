/* ═════════════════════════════════════════════════════════════════════
   小说管理App · 共享应用逻辑
   所有页面通用的：状态读写、身份验证、演示模式、工具函数
   ═════════════════════════════════════════════════════════════════════ */

var SHELF_KEY = 'bookapp_shelf_v1';
var USER_KEY  = 'bookapp_user_v1';
var USERS_KEY = 'bookapp_users_v1';

/* ─── 状态 ────────────────────────────────────────────────────────── */
function getShelf() { try { return JSON.parse(localStorage.getItem(SHELF_KEY)) || []; } catch(e) { return []; } }
function saveShelf(arr) { localStorage.setItem(SHELF_KEY, JSON.stringify(arr)); }
function getCurrentUser() { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch(e) { return null; } }
function saveCurrentUser(u) { if (u) localStorage.setItem(USER_KEY, JSON.stringify(u)); else localStorage.removeItem(USER_KEY); }
function getUsers() { try { return JSON.parse(localStorage.getItem(USERS_KEY)) || []; } catch(e) { return []; } }
function saveUsers(arr) { localStorage.setItem(USERS_KEY, JSON.stringify(arr)); }

/* ─── 认证守卫 ────────────────────────────────────────────────────── */
function requireAuth() {
  var user = getCurrentUser();
  if (!user) { window.location.href = 'login.html'; return null; }
  return user;
}

/* 演示模式：未登录时自动创建演示账号 + 3 本示例书籍 */
function requireAuthOrDemo() {
  var user = getCurrentUser();
  if (user) { initAvatar(user); return user; }
  user = { email: 'demo@example.com' };
  saveCurrentUser(user);
  var users = getUsers();
  if (!users.find(function(u) { return u.email === 'demo@example.com'; })) {
    users.push({ email: 'demo@example.com', password: 'demo1234' });
    saveUsers(users);
  }
  var shelf = getShelf();
  if (shelf.length === 0) {
    shelf = [
      { id: 'demo-1', title: '星辰变',   author: '我吃西红柿',  sourceUrl: 'https://www.qidian.com/book/118447/',      status: 'done', chapterCount: 488, addedAt: Date.now() - 86400000*2, chapters: [] },
      { id: 'demo-2', title: '诡秘之主', author: '爱潜水的乌贼', sourceUrl: 'https://www.qidian.com/book/1010868264/', status: 'idle', chapterCount: 0,   addedAt: Date.now() - 86400000,   chapters: [] },
      { id: 'demo-3', title: '大王饶命', author: '会说话的肘子',  sourceUrl: null,                                                      status: 'idle', chapterCount: 0,   addedAt: Date.now(),              chapters: [] }
    ];
    saveShelf(shelf);
  }
  initAvatar(user);
  return user;
}

function initAvatar(user) {
  var av = document.getElementById('user-avatar-display');
  if (av) av.textContent = (user.email || 'U').charAt(0).toUpperCase();
}

/* ─── 退出 ────────────────────────────────────────────────────────── */
function doLogout() { saveCurrentUser(null); localStorage.removeItem(USER_KEY); window.location.href = 'login.html'; }

/* ─── 工具 ────────────────────────────────────────────────────────── */
function escHtml(str) { var d = document.createElement('div'); d.textContent = str; return d.innerHTML; }
function showToast(msg) {
  var t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg; t.style.display = '';
  clearTimeout(t._tid); t._tid = setTimeout(function() { t.style.display = 'none'; }, 2000);
}
function formatDate(ts) { return new Date(ts).toLocaleDateString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit' }); }
function coverClass(title) { return 'c' + (title.charCodeAt(0) % 8); }
function genId() { return crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2); }
function statusBadge(status) {
  var map = { idle: ['badge-idle','待抓取'], crawling: ['badge-crawl','抓取中'], done: ['badge-done','已完成'], failed: ['badge-failed','抓取失败'] };
  var s = map[status] || map.idle;
  return '<span class="badge ' + s[0] + '">' + s[1] + '</span>';
}

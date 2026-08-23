/* ═══════════════════════════════════════════════════
   小说管理App · 搜索查询意图识别（v2.1 新增）
   判断用户在书架内输入的查询是「书名 / 作者名」（适合普通
   模糊搜索）还是「自然语言描述」（适合 AI 语义搜索）。
   纯函数、无副作用，便于单元测试与复用。

   识别原则（保守默认）：
   - 明确信号（口语词 / 语气词 / 标点 / 题材描述）→ AI；
   - 识别存疑时一律按普通搜索，避免误触 AI 接口；
   - 题材词（玄幻/修仙/重生…）只按「前缀+题材」或「题材+后缀」
     上下文匹配，不做裸子串匹配——否则《凡人修仙传》等真实
     书名会被误判为自然语言描述。
   ═══════════════════════════════════════════════════ */

/** 识别出的搜索意图：普通关键词搜索 / AI 自然语言语义搜索 */
export type QueryIntent = 'normal' | 'ai'

/** 分类题材词（只参与上下文匹配，不做裸子串匹配） */
const GENRES =
  '玄幻|奇幻|修仙|修真|仙侠|武侠|科幻|悬疑|推理|侦探|言情|都市|历史|军事|网游|末世|重生|穿越|系统|爽文|甜宠|虐文|热血|治愈|黑暗|轻小说'

/** 题材词前缀：想 / 要 / 找 / 看 / 读 / 喜欢 / 最近 / 求 + 题材词（中间允许 0-3 字） */
const GENRE_WITH_PREFIX = new RegExp(`(想|要|找|看|读|喜欢|最近|求).{0,3}(${GENRES})`)

/** 题材词后缀：题材词 + 小说 / 文 / 书 / 题材 / 类 等 */
const GENRE_WITH_SUFFIX = new RegExp(`(${GENRES})(题材|小说|文|书|故事|类型|类|的)`)

/** 题材词单独出现（「玄幻」「修仙小说」的省略表达） */
const GENRE_ONLY = new RegExp(`^(${GENRES})$`)

/**
 * 中文口语 / 描述词（裸子串匹配）。
 * 已剔除题材词（另走上下文匹配）与「的/书/本/部」等
 * 会命中真实书名/作者名的弱信号词。
 */
const COLLOQUIAL_WORDS = [
  '想看', '想找', '想读', '想搜', '找一本', '找一部', '找点', '找些', '找本',
  '最近看', '类似', '推荐', '有没有', '帮我找', '给我找', '求推荐',
  '无聊', '打发时间', '睡前', '轻松', '搞笑', '好看', '经典',
  '完结', '连载', '长篇', '短篇', '字数多', '烧脑'
]

/** 英文口语 / 描述词（单词边界匹配，避免 "bread" 误中 "read"） */
const ENGLISH_COLLOQUIAL =
  /(^|[^a-z])(want|looking\s+for|find|recommend|about|like|similar|read|interesting|good)([^a-z]|$)/i

/** 中文语气词 / 句末词：只出现于句子而非书名（已剔除「的」，书名中太常见） */
const FILLER_WORDS = ['吗', '呢', '吧', '啊', '呀', '哦', '嘛', '哈', '了', '一些', '一下', '有点']

/** 英文虚词 / 量词（单词边界匹配） */
const ENGLISH_FILLER = /(^|[^a-z])(a|an|the|of|to|for|and|some|book|novel|story)([^a-z]|$)/i

/** 常见标点符号（含中英文句读；不含 · ' . 以免误伤书名与缩写名，如 J.K. Rowling） */
const PUNCTUATION = /[，。！？、；：,!?;:“”‘’]+/

/** 书名号 / 引号包裹：视为精确书名，按普通搜索 */
const WRAPPED_TITLE = /《[^》]{1,40}》|"[^"]{2,40}"|「[^」]{1,40}」/

/** 词段数阈值：按空格/中英文切换切分 ≥3 段视为自然语言描述 */
const MAX_WORD_SEGMENTS = 3

/** 判断字符是否为「中文字符」（含 CJK 扩展，排除标点） */
function isCjkChar(ch: string): boolean {
  return /[㐀-䶿一-鿿豈-﫿]/.test(ch)
}

/** 判断字符是否为「中英文单词字符」（用于词段统计；含点号——J.K. 这类首字母缩写视为同一词段） */
function isWordChar(ch: string): boolean {
  return isCjkChar(ch) || /[a-zA-Z0-9.]/.test(ch)
}

/** 查询是否包含空格分隔的词段 ≥3（书名/作者名不带空格，多词描述才会命中） */
function hasManyWordSegments(q: string): boolean {
  let segments = 0
  let prevIsWord = false
  for (const ch of q) {
    const isWord = isWordChar(ch)
    if (isWord && !prevIsWord) segments++
    prevIsWord = isWord
  }
  return segments >= MAX_WORD_SEGMENTS
}

/** 查询是否为「纯字母数字 + 空格」的短串（外文书名/作者，如 "XIAO JING"） */
function isShortPlainAlnum(q: string): boolean {
  return q.length <= 20 && /^[a-zA-Z0-9]+(\s+[a-zA-Z0-9]+){0,2}$/.test(q)
}

/**
 * 识别搜索意图（v2.1）：
 * - 超短（<2 字符）或过长（>60 字符）输入一律按普通搜索（常规边界回退）；
 * - 书名号/引号包裹、题材描述、口语词、语气词、标点、多词段
 *   → 自然语言描述，返回 'ai'；
 * - 其余（典型书名 / 作者名）→ 'normal'。
 *
 * 返回 'normal' 是保守默认：识别存疑时用普通搜索，避免误触 AI 接口。
 */
export function detectQueryIntent(raw: string): QueryIntent {
  const q = raw.trim()
  if (q.length < 2 || q.length > 60) return 'normal'

  // 书名号 / 引号包裹的精确书名 → 普通搜索
  if (WRAPPED_TITLE.test(q)) return 'normal'

  // 题材词上下文匹配（去掉空格后判断：「玄幻 小说」与「玄幻小说」等价）
  const compact = q.replace(/\s+/g, '')
  if (GENRE_ONLY.test(compact)) return 'ai'
  if (GENRE_WITH_PREFIX.test(compact) || GENRE_WITH_SUFFIX.test(compact)) return 'ai'

  // 英文口语词（单词边界）
  if (ENGLISH_COLLOQUIAL.test(q)) return 'ai'

  // 中文口语 / 描述词
  if (COLLOQUIAL_WORDS.some((w) => q.includes(w))) return 'ai'

  // 英文虚词（单词边界，如 "a" / "of" / "novel"）
  if (ENGLISH_FILLER.test(q)) return 'ai'

  // 中文语气词 → 句子而非书名
  if (FILLER_WORDS.some((w) => q.includes(w))) return 'ai'

  // 标点出现 → 句子而非书名
  if (PUNCTUATION.test(q)) return 'ai'

  // 纯字母数字短串 → 外文书名 / 作者名，普通搜索
  if (isShortPlainAlnum(q)) return 'normal'

  // 空格词段 ≥3 → 自然语言描述
  if (hasManyWordSegments(q)) return 'ai'

  return 'normal'
}

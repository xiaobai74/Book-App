/* ═══════════════════════════════════════════════
   小说管理App · 搜索查询意图识别单元测试（v2.1）
   覆盖：书名 / 作者名 / 自然语言描述 / 边界情况。
   ═══════════════════════════════════════════════ */
import { describe, it, expect } from 'vitest'
import { detectQueryIntent } from '../src/lib/queryIntent'

describe('detectQueryIntent — 书名 / 作者名（普通搜索）', () => {
  it.each([
    '诛仙',           // 典型书名
    '凡人修仙传',      // 含题材词的复合书名，不能被题材词误伤
    '斗破苍穹',
    '三体',
    '雪中悍刀行',
    '庆余年',
    '全职高手',
    '鬼吹灯',
    '盗墓笔记',
    '斗罗大陆',
    '完美世界',
    '诡秘之主',
    '剑来',
    '道诡异仙',        // 含"诡异"但不含题材词
    '天蚕土豆',        // 作者名
    '唐家三少',        // 作者名
    '辰东',
    '金庸',
    '余华',
    '莫言',
    '刘慈欣',
    '东野圭吾',
    '乌贼',            // 作者昵称
    '鲁迅',
    '《三体》',        // 书名号包裹的精确书名
    '《凡人修仙传》',
    '"The Hobbit"',    // 引号包裹的英文书名
    '「活着」',
    'harry potter',    // 纯字母数字 + 空格的外文书名
    'XIAO JING',       // 全大写外文书名
    'J.K. Rowling',    // 含点号的作者名（点号不在标点集合中，短串按普通）
    'George Orwell',
    '诛仙 第一部',      // 空格+短词段，不带描述信号
    '盗墓笔记 第二卷',
    'j',               // 超短输入回退普通
    'a',               // 超短输入回退普通
  ])('「%s」→ normal', (q) => {
    expect(detectQueryIntent(q)).toBe('normal')
  })
})

describe('detectQueryIntent — 自然语言描述（AI 语义搜索）', () => {
  it.each([
    '我想看修仙小说',        // 口语词 + 题材后缀
    '想看玄幻小说',
    '想看玄幻',
    '想找本好看的修仙文',
    '帮我找一部都市言情小说',
    '最近看的那本修仙小说',
    '推荐几本悬疑推理的',
    '有没有类似斗破苍穹的小说',  // 口语词「有没有」+「类似」
    '找点轻松搞笑的',
    '无聊时看的书',
    '睡前读的小说',
    '最近比较火的完结小说',
    '有没有长篇的玄幻',          // 「的」触发（语气词集合）
    '求推荐热血爽文',            // 口语词「求推荐」/ 题材后缀
    '玄幻',                      // 题材词单独出现
    '轻小说',
    '想看',                      // 口语词
    '推荐点书',                  // 口语词「推荐」+「书」（后缀）
    '想找的书，最近看的都行',     // 标点触发
    '有什么好看的推荐吗？',       // 标点 + 语气词
    '帮我找一下吧',               // 语气词「吧」
    '最近有点无聊，求点好看的玄幻小说', // 综合信号
    '我喜欢看悬疑小说',           // 「喜欢」前缀 + 题材后缀
    'find me a fantasy novel',   // 英文口语词
    'I want to read something interesting', // 英文口语词 + 虚词
    'books about cultivation',   // 英文虚词 about
    'recommend some good novels', // 英文口语词 recommend
    'find 修仙 novel',           // 空格词段 ≥3 + 英文虚词
    'a good story',              // 英文虚词 + 词段 ≥3
    '轻松搞笑',                   // 口语词「轻松」「搞笑」
    '好看的玄幻',                 // 口语词「好看」+ 题材后缀
  ])('「%s」→ ai', (q) => {
    expect(detectQueryIntent(q)).toBe('ai')
  })
})

describe('detectQueryIntent — 边界情况', () => {
  it('空白输入 → normal', () => {
    expect(detectQueryIntent('')).toBe('normal')
    expect(detectQueryIntent('   ')).toBe('normal')
  })

  it('超过 60 字符 → normal（保守回退）', () => {
    expect(detectQueryIntent('这是一段非常长的自然语言描述'.repeat(5))).toBe('normal')
  })

  it('首尾空格被裁剪后再判断', () => {
    expect(detectQueryIntent('  诛仙  ')).toBe('normal')
    expect(detectQueryIntent('  想看修仙  ')).toBe('ai')
  })
})

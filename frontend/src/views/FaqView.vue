<script setup lang="ts">
import { ref } from 'vue'

interface FaqItem {
  id: string
  q: string
  a: string
}

// FAQ 內容刻意以純資料 + 純文字呈現，方便 prerender 與搜尋引擎完整抓取。
const FAQS: FaqItem[] = [
  {
    id: 'help-me-pick',
    q: '這個工具能幫我選到會漲的股票嗎？',
    a: '不能。DestinyOrder 的核心是「隨機抽選」，它沒有也不假裝有任何選股 alpha。它的價值在於「打破你選股的盲點」、「強迫你研究不熟悉的標的」、「對抗確認偏誤」。如果你期待的是能穩定提供「明牌」的工具，那 DestinyOrder 並不適合這種用途——對多數一般投資人而言，低成本、分散化的 ETF 長期持有，通常是更常見、也更被學術支持的投資方式。',
  },
  {
    id: 'why-these-5-etfs',
    q: '為什麼選擇 0050、006208、009816、00403A、00981A 這 5 檔 ETF？',
    a: '這 5 檔橫跨兩條主軸：被動市值型（0050 / 006208 / 009816 均屬台股大型權值股級別產品）與主動式股票 ETF（00403A / 00981A）。透過這個組合，候選池既包含市值龍頭，又納入主動式 ETF 所挑選的中大型股，提供有別於單一市值排序的研究視角。',
  },
  {
    id: 'twin-etfs',
    q: '0050、006208、009816 不是都追蹤台股前 50 大嗎？為什麼三檔都列？',
    a: '是的，三者本質都鎖定台股市值前 50 大，但發行商與設計細節不同：0050（元大）是歷史最悠久的旗艦；006208（富邦）追蹤同一個臺灣 50 指數但費用較低；009816（凱基）追蹤的是「特選臺灣 TOP 50 指數」，額外要求成分股近四季獲利為正，並採股息再投資、不對外配息的設計。同時收錄三者讓「成分股一覽」頁能更直觀看出「哪些股票被多檔同類型 ETF 重複收錄」的訊號。',
  },
  {
    id: 'active-etfs',
    q: '00403A 和 00981A 標示「A」是什麼意思？',
    a: '依金管會新制，台股 ETF 代號的第六碼為 A 者代表「主動式股票 ETF」（D 則為主動式債券 ETF），A 即 Active 縮寫。相對於傳統被動追蹤指數的 ETF，主動式 ETF 不追蹤特定指數，而是由經理人主動選股、試圖戰勝對應指標。00403A（統一台股升級 50 主動式 ETF）以大型權值股為核心、輔以主動選股汰弱留強，市場稱為「升級版 0050」；00981A（統一台股增長主動式 ETF）聚焦台灣大型與成長型企業，尋找具創新能力與長期成長潛力的公司。兩者共同提供「主動選股」視角，與被動市值型 ETF 形成互補。',
  },
  {
    id: 'what-is-holding',
    q: '「成分股」是什麼意思？',
    a: 'ETF 是一籃子股票的組合，「成分股」就是這個籃子裡實際持有的個股。例如 0050 的成分股，就是台積電、鴻海、聯發科等 50 檔台灣市值前段班的公司。每檔成分股在 ETF 中各占一定的「權重」，權重越高，這檔個股對 ETF 整體淨值的影響就越大。',
  },
  {
    id: 'data-refresh',
    q: '權重資料多久更新一次？是即時的嗎？',
    a: '不是即時。資料由背景程式自動從各 ETF 發行商官網抓取，更新頻率受限於官方公告時程（多為每日盤後或每週更新），並非交易時間內的即時資料。實際資料抓取日期會顯示在每個頁面上。投資決策請以發行商官方資料為準。',
  },
  {
    id: 'can-i-buy',
    q: '抽出來的標的我可以直接買嗎？',
    a: '工具上的「抽選結果」絕對不是買進建議，只是一個「請你今天去研究這檔」的提示。是否買進，必須由你自己評估這檔股票的基本面、產業地位、財報、估值與你個人的投資組合需求。任何單純依照隨機抽選結果而做出的買賣決策，都不在本工具設計用途之內，盈虧由使用者自負。',
  },
  {
    id: 'why-slot-machine',
    q: '為什麼還做了拉霸機？只是好玩嗎？',
    a: '行為經濟學告訴我們，人類對「隨機獎勵」的多巴胺反應遠強於理性決策。遊戲化（gamification）與隨機獎勵設計能讓「選股研究」這個本質偏枯燥的流程，更容易被長期維持。我們設計拉霸機的目的不是鼓勵交易，而是讓你「願意每天打開研究股票」——當研究變成長期習慣，你對市場的理解通常也會比多數人更系統化。',
  },
  {
    id: 'academic-support',
    q: '隨機選股有學術研究支持嗎？',
    a: '有間接支持。Burton Malkiel 在《漫步華爾街》提出「蒙眼猴子飛鏢」的著名比喻；Eugene Fama 的效率市場假說指出，在半強式效率假設下，單靠公開資訊長期取得顯著超額報酬會相當困難；S&P Global 的 SPIVA 報告長期顯示，多數主動基金扣除費用後績效跑輸對應指數（美國大型股 10 年期跑輸比例常高達 80% 以上）。這些研究共同指向的結論並不是「隨機選股 = 認真研究」，而是：對一般投資人而言，低成本、高分散的被動投資往往比頻繁主動選股更具長期優勢；而在已經高度分散的候選池中隨機選股，是一種降低研究偏誤、強迫接觸陌生標的的合理方法。',
  },
  {
    id: 'self-pick-vs-etf',
    q: '用 ETF 成分股自選組合，會比直接買 ETF 好嗎？',
    a: '對絕大多數一般投資人來說，答案是「不會」。原因包括：（1）你必須假設自己有穩定的選股 alpha，但連專業基金經理人都做不到；（2）自組會產生額外的手續費、證交稅、買賣價差；（3）ETF 的再平衡由發行商自動執行，你自組需親自追蹤。對多數一般投資人而言，學術實證通常較支持低成本、分散化的指數投資，而非頻繁自選成分股交易。',
  },
  {
    id: 'duplicate-holdings-signal',
    q: '為什麼「成分股一覽」要按共同持有 ETF 筆數排序？',
    a: '當一檔股票同時出現在多檔 ETF 中，代表它同時符合多種篩選條件——例如市值、流動性、獲利能力、產業代表性或經理人偏好——可作為額外觀察與研究優先度排序的參考。需要注意的是，0050 與 006208 追蹤同一個指數，並非獨立的篩選邏輯；但若一檔股票同時出現在被動市值型 ETF 與主動式 ETF 之中，這項提示的強度通常會比兩檔同類型 ETF 同時命中更高。這是一個簡單但實用的啟發式。',
  },
  {
    id: 'add-more-etfs',
    q: '我可以建議增加新的 ETF 嗎？',
    a: '歡迎透過下方 GitHub Issues 提出建議。我們會優先考慮：（1）規模較大、追蹤指數具代表性的；（2）能補強現有候選池產業 / 主題覆蓋度的；（3）資料來源公開且更新規律的。注意：純債券型、貨幣型、海外 ETF 不在當前範圍內。',
  },
  {
    id: 'privacy',
    q: '網站會收集我的個資嗎？',
    a: '本站不要求註冊、不要求登入，不主動收集任何個人識別資訊，亦未接入第三方廣告追蹤服務。',
  },
  {
    id: 'contact',
    q: '我有意見回饋或功能建議，怎麼聯絡？',
    a: '歡迎透過專案 GitHub Issues（https://github.com/LaimoKarca/DestinyOrder/issues）提交問題回報、新功能建議或 ETF 收錄請求。',
  },
]

// 預設展開第一題，提示使用者這是可摺疊清單
const open_ids = ref<Set<string>>(new Set(['help-me-pick']))

function toggle(id: string): void {
  if (open_ids.value.has(id)) {
    open_ids.value.delete(id)
  } else {
    open_ids.value.add(id)
  }
  // 因為 Set 是 mutable，要 trigger 響應式
  open_ids.value = new Set(open_ids.value)
}
</script>

<template>
  <main class="faq-page">
    <article class="faq-article">
      <header class="hero">
        <span class="eyebrow">常見問題 FAQ</span>
        <h1>關於 DestinyOrder <br class="br-mobile" />你可能想問的事</h1>
        <p class="lede">
          這裡整理了關於工具使用、學術依據、資料來源與投資觀念的常見問題。<br class="br-desktop" />
          如果你有其他疑問，歡迎透過頁面底部 GitHub Issues 與我們聯繫。
        </p>
      </header>

      <ul class="faq-list">
        <li
          v-for="item in FAQS"
          :key="item.id"
          class="faq-item"
          :class="{ 'is-open': open_ids.has(item.id) }"
        >
          <button
            type="button"
            class="faq-question"
            :aria-expanded="open_ids.has(item.id)"
            :aria-controls="`faq-answer-${item.id}`"
            @click="toggle(item.id)"
          >
            <span class="q-mark" aria-hidden="true">Q</span>
            <span class="q-text">{{ item.q }}</span>
            <span class="q-arrow" aria-hidden="true">›</span>
          </button>
          <div
            :id="`faq-answer-${item.id}`"
            class="faq-answer"
            role="region"
          >
            <span class="a-mark" aria-hidden="true">A</span>
            <p>{{ item.a }}</p>
          </div>
        </li>
      </ul>

      <footer class="faq-footer">
        <p>
          沒有找到你想問的問題？
          歡迎前往
          <a
            href="https://github.com/LaimoKarca/DestinyOrder/issues"
            target="_blank"
            rel="noopener noreferrer"
            class="mail-link"
          >GitHub Issues</a>
          提交回饋。
        </p>
      </footer>
    </article>
  </main>
</template>

<style scoped>
.faq-page {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  padding: clamp(1.5rem, 5vw, 4rem) clamp(1rem, 4vw, 3rem)
    calc(var(--app-footer-height) + clamp(1.2rem, 3vw, 2rem));
  color: #e8eaf6;
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
  background:
    radial-gradient(1200px 600px at 10% -20%, #2a1f6b 0%, transparent 60%),
    radial-gradient(900px 500px at 110% 10%, #1e4778 0%, transparent 55%),
    linear-gradient(180deg, #0b0f24 0%, #070a1a 100%);
  overflow-x: hidden;
}

.faq-article {
  max-width: 1040px;
  margin: 0 auto;
}

.hero {
  text-align: center;
  margin-bottom: clamp(2rem, 5vw, 3rem);
}

.eyebrow {
  display: inline-block;
  padding: 0.35rem 0.9rem;
  font-size: clamp(0.7rem, 2.4vw, 0.78rem);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #c9c6f6;
}

.hero h1 {
  margin: 0.9rem 0 0.8rem;
  font-size: clamp(1.55rem, 5vw, 2.4rem);
  font-weight: 800;
  line-height: 1.3;
  background: linear-gradient(90deg, #fff 0%, #b3b8ff 60%, #7ec8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.lede {
  margin: 0 auto;
  max-width: 580px;
  font-size: clamp(0.9rem, 2.6vw, 1rem);
  line-height: 1.8;
  color: #b1b6d6;
}

.faq-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.faq-item {
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: clamp(12px, 2.4vw, 16px);
  background:
    linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.04) 0%,
      rgba(255, 255, 255, 0.015) 100%
    );
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  overflow: hidden;
  transition:
    border-color 0.25s ease,
    background 0.25s ease;
}

.faq-item.is-open {
  border-color: rgba(179, 184, 255, 0.32);
  background:
    linear-gradient(
      180deg,
      rgba(126, 200, 255, 0.06) 0%,
      rgba(124, 92, 255, 0.04) 100%
    );
}

.faq-question {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: clamp(0.85rem, 2.8vw, 1.1rem) clamp(0.9rem, 2.8vw, 1.4rem);
  background: transparent;
  border: 0;
  color: inherit;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  font-size: clamp(0.95rem, 2.7vw, 1.05rem);
  font-weight: 600;
  line-height: 1.5;
  transition: background 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}

.faq-question:hover {
  background: rgba(255, 255, 255, 0.03);
}

.q-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #b3b8ff 0%, #7ec8ff 100%);
  color: #0b0f24;
  font-weight: 800;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.q-text {
  flex: 1;
  color: #f0f2ff;
}

.q-arrow {
  font-size: 1.4rem;
  color: #5e6285;
  transform: rotate(90deg);
  transition: transform 0.25s ease, color 0.25s ease;
}

.faq-item.is-open .q-arrow {
  transform: rotate(-90deg);
  color: #b3b8ff;
}

.faq-answer {
  display: none;
  padding: 0 clamp(0.9rem, 2.8vw, 1.4rem) clamp(0.85rem, 2.6vw, 1.1rem);
  gap: 0.8rem;
}

.faq-item.is-open .faq-answer {
  display: flex;
}

.a-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(179, 184, 255, 0.25);
  color: #b3b8ff;
  font-weight: 800;
  font-size: 0.85rem;
  flex-shrink: 0;
  margin-top: 0.15rem;
}

.faq-answer p {
  margin: 0;
  flex: 1;
  font-size: clamp(0.88rem, 2.5vw, 0.95rem);
  line-height: 1.85;
  color: #c9cce8;
}

.faq-footer {
  margin-top: clamp(2rem, 4vw, 2.8rem);
  padding: 1.2rem;
  text-align: center;
  border-radius: 14px;
  border: 1px dashed rgba(179, 184, 255, 0.25);
  background: rgba(255, 255, 255, 0.02);
}

.faq-footer p {
  margin: 0;
  font-size: clamp(0.88rem, 2.5vw, 0.95rem);
  line-height: 1.8;
  color: #b1b6d6;
}

.mail-link {
  color: #b3b8ff;
  text-decoration: underline;
  text-decoration-color: rgba(179, 184, 255, 0.4);
  text-underline-offset: 3px;
  transition: color 0.2s ease;
}

.mail-link:hover {
  color: #fff;
  text-decoration-color: #fff;
}

.br-mobile {
  display: none;
}

.br-desktop {
  display: inline;
}

@media (max-width: 540px) {
  .faq-question {
    padding: 0.85rem 0.9rem;
    gap: 0.6rem;
  }
  .faq-answer {
    padding: 0 0.9rem 0.85rem;
    gap: 0.6rem;
  }
  .br-mobile {
    display: inline;
  }
  .br-desktop {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .q-arrow,
  .faq-item {
    transition: none !important;
  }
}
</style>

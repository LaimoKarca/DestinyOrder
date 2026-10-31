<script setup lang="ts">
// 純文字長文頁，刻意不帶 store / API，讓 prerender 結果為純靜態 HTML，
// 方便 AdSense 與 Googlebot 在不執行 JS 的情況下也能讀到完整內容。
</script>

<template>
  <main class="about-page">
    <article class="about-article">
      <header class="hero">
        <span class="eyebrow">關於 DestinyOrder</span>
        <h1>為什麼我們需要一個<br class="br-mobile" />「隨機選股」的工具？</h1>
        <p class="lede">
          DestinyOrder 是一個圍繞著台灣股票市場的小型研究工具，核心功能是「從台灣熱門的市值型與主動式
          ETF 成分股中，以隨機抽選的方式提供研究標的」。看似嬉鬧的「抽抽樂」與「拉霸機」介面背後，
          其實隱含著一個被多數投資者忽略的命題——
          <strong>在已經高度分散、且經過初步篩選的候選池中，隨機選擇本身就是一種降低研究偏誤、強迫接觸陌生標的的有效方法。</strong>
        </p>
      </header>

      <section class="section">
        <h2>一、為什麼要做這個工具？選股困境的真相</h2>
        <p>
          截至 2026 年，台灣上市、上櫃與興櫃公司合計已逾 2000 家。對於一般投資人來說，
          光是要「決定今天要研究哪一檔」就已經是嚴重的資訊過載問題。實務上，多數人最後會落入兩個典型陷阱：
        </p>
        <ol>
          <li>
            <strong>近期偏誤（Recency Bias）：</strong>只研究今天上漲、被新聞點名、
            被理財社群討論的股票，導致研究池高度集中在少數熱門股，而錯過大量的中型股與冷門產業。
          </li>
          <li>
            <strong>確認偏誤（Confirmation Bias）：</strong>因為演算法推薦的關係，
            投資人會反覆看到自己已經追蹤、已經持有的股票相關訊息，這加深了選股偏好的封閉性，
            使投資組合愈來愈缺乏分散性。
          </li>
        </ol>
        <p>
          DestinyOrder 嘗試提供的解法極為樸素：
          <strong>用一個「隨機抽選 ETF 成分股」的小工具，每天為你推一檔你原本可能不會點開的標的。</strong>
          由於候選池來自 0050、006208、009816、00403A、00981A 五檔 ETF 的成分股，
          相較於從全市場隨機抽樣，這些公司多半已通過發行商或經理人基於市值、流動性、
          獲利能力等指標的初步篩選，候選標的的品質基線會相對穩定。
        </p>
      </section>

      <section class="section">
        <h2>二、隨機選股的學術依據：被嚴重低估的一條路</h2>

        <h3>2.1 隨機漫步假說（Random Walk Hypothesis）</h3>
        <p>
          1973 年，普林斯頓大學經濟學教授 Burton Malkiel 在其經典著作《漫步華爾街》(A Random Walk
          Down Wall Street) 中提出一個極具爭議性的論點：
        </p>
        <blockquote>
          「一隻被蒙著眼睛的猴子，朝著報紙的股票版投擲飛鏢，所選出的投資組合，績效不會輸給專家謹慎挑選的組合。」
        </blockquote>
        <p>
          這句話經常被斷章取義，但其原意是指出短期股價變動具有高度隨機性，
          <strong>穩定、持續地透過短期資訊優勢擊敗市場極其困難。</strong>
          後續半個世紀的學術文獻與基金績效統計大致支持這個方向。
          當然，學界後續也發展出 factor investing、動能效應、品質因子等
          可帶來長期超額報酬的「異常現象」，但這些通常需要嚴謹的方法論與紀律才能實現，
          並非單靠閱讀新聞或追熱門股就能取得。
        </p>

        <h3>2.2 效率市場假說（Efficient Market Hypothesis, EMH）</h3>
        <p>
          芝加哥大學的 Eugene Fama（2013 年諾貝爾經濟學獎得主）自 1960 年代開始陸續發展效率市場假說，
          並在 1970 年發表的經典論文中將其完整定型，
          將市場效率區分為弱式、半強式、強式三種。在「半強式效率」的假設下，所有公開資訊都已被反映在股價中，
          換言之，任何根據已公布的財報、新聞、產業報告所做的選股決策，
          <strong>其超額報酬（alpha）在長期上通常難以穩定持續存在。</strong>
        </p>
        <p>
          這意味著：若市場接近半強式效率，
          <strong>單靠閱讀公開資訊就想長期、穩定取得顯著超額報酬會相當困難。</strong>
          這也是為什麼許多研究認為，對一般投資人而言，
          低成本、分散化的被動投資往往比頻繁主動選股更具長期優勢。
          換句話說，「認真研究」並非沒有意義，
          但你必須認清：你的研究要打敗的，不是隨機，而是無數比你更早、更專業、資訊更完整的市場參與者。
        </p>

        <h3>2.3 SPIVA 報告：主動選股的長期慘敗</h3>
        <p>
          S&amp;P Global 每半年發布一次的 SPIVA (S&amp;P Indices Versus Active) 報告，
          系統性地比較主動式基金與其對應指標（被動指數）的長期績效。歷年數據呈現一致的結論：
        </p>
        <ul>
          <li>截至 2024 年底，在美國大型股市場，過去 10 年扣除費用後跑輸對應指數的主動基金比例常達 <strong>80% 以上</strong>。</li>
          <li>時間拉得愈長（15 年、20 年），跑輸比例普遍只會持平或攀升，鮮少下降。</li>
          <li>即使在新興市場、小型股等理論上「市場較無效率、選股空間較大」的領域，主動基金也未能展現持續性的優勢。</li>
        </ul>
        <p>
          這份報告的含義是值得思考的：擁有彭博終端、研究團隊、CFA 與博士學位的專業基金經理人，
          長期績效多數仍輸給「按權重持有指數」的被動策略。
          那麼，一般散戶花幾小時自行研究選股，要持續贏過大盤的勝率有多高？這是值得每個投資人誠實面對的問題。
        </p>
      </section>

      <section class="section">
        <h2>三、從 ETF 成分股下手的方法論</h2>
        <p>
          DestinyOrder 的核心設計，是把候選池限縮在「五檔台灣熱門 ETF 的成分股」，
          這背後有一個明確的方法論思考：<strong>讓 ETF 發行商先幫你做完第一輪篩選。</strong>
        </p>

        <h3>3.1 ETF 已內建篩選邏輯</h3>
        <p>
          DestinyOrder 選擇的這 5 檔 ETF，可以分成「<strong>被動市值型</strong>」與「<strong>主動式選股</strong>」兩條軸線：
        </p>
        <ul>
          <li><strong>0050（元大台灣 50）</strong>：台灣第一檔 ETF，由元大投信發行，追蹤「臺灣 50 指數」，涵蓋台股市值前 50 大公司，是台股核心資產配置的代表。</li>
          <li><strong>006208（富邦台 50）</strong>：由富邦投信發行，追蹤與 0050 相同的「臺灣 50 指數」，長期內扣費用相對較低，與 0050 成分股高度重疊。</li>
          <li><strong>009816（凱基台灣 TOP 50）</strong>：由凱基投信發行，追蹤「特選臺灣 TOP 50 指數」，選股以大型權值股為核心，但除市值之外也加入「近四季稅後純益為正」等獲利篩選條件，整體偏向「大型股 + 品質篩選」設計；同時是台灣首檔不配息、股息自動再投資的台股 ETF。</li>
          <li><strong>00403A（統一台股升級 50 主動式 ETF）</strong>：第六碼為「A」代表主動式股票 ETF；由統一投信發行，不追蹤特定指數，以大型權值股為核心、輔以主動選股與汰弱留強，市場常稱為「升級版 0050」。</li>
          <li><strong>00981A（統一台股增長主動式 ETF）</strong>：同為主動式股票 ETF；由統一投信發行，投資方向聚焦台灣大型與成長型企業，透過主動選股尋找具創新能力與長期成長潛力的公司。</li>
        </ul>
        <p>
          這意味著「成分股一覽」分頁的每一檔股票，
          都至少通過了一個專業團隊「值得放進指數 / 主動 ETF」的判斷。
          這是台灣上市櫃股票中，相對經過規模、流動性或策略條件第一輪篩選的一批候選池。
          同時，因為候選池橫跨「被動極致集中 TOP 50」與「主動式中大型股精選」兩條軸線，
          抽到的標的會自然涵蓋市值龍頭與部分被市場視為具成長潛力的中大型股，視角不會過於偏狹。
        </p>

        <h3>3.2 共同持有筆數作為隱性訊號</h3>
        <p>
          當一檔股票同時出現在多檔 ETF 中，代表它同時符合多種篩選條件——
          例如市值、流動性、獲利能力、產業代表性或經理人偏好——
          因此可視為一種值得額外關注的訊號。
          需要注意的是，0050 與 006208 追蹤同一個指數，並非「獨立」的篩選邏輯；
          但若一檔股票同時出現在被動市值型 ETF 與主動式 ETF 之中，
          訊號強度通常會比兩檔同類型 ETF 同時命中更高。
        </p>
        <p>
          這也是為什麼「成分股一覽」頁面預設按照「共同持有 ETF 筆數」由多至少排序——
          這是一個簡單但實用的啟發式（heuristic）。
        </p>

        <h3>3.3 學術問題：用成分股自組，會贏過直接買 ETF 嗎？</h3>
        <p>
          這是一個值得深入研究的命題。理論上，如果你能精準從 ETF 成分股中挑出未來表現最好的子集合，
          並用更高的權重持有，你的績效有機會「賽過」ETF 本身。
          但這個策略面臨幾個結構性挑戰：
        </p>
        <ol>
          <li>
            <strong>選股能力假設：</strong>你必須假設自己具備穩定的選股 alpha，
            而 SPIVA 報告告訴我們，連專業經理人都做不到這點。
          </li>
          <li>
            <strong>交易成本：</strong>自組投資組合每次調整都會產生手續費、證交稅、買賣價差，
            台股的內扣總費用通常仍低於頻繁交易的散戶總成本。
          </li>
          <li>
            <strong>再平衡負擔：</strong>ETF 會自動依規則進行成分調整（每季 / 每半年）並由發行商承擔交易成本；
            你自組則必須親自追蹤指數異動並執行交易。
          </li>
          <li>
            <strong>管理負擔：</strong>ETF 內部的成分調整與配息流程由發行商統一處理，
            可降低投資人自行追蹤、再平衡與頻繁交易的管理成本。
          </li>
        </ol>
        <p>
          因此，學術上多數實證研究的結論是：
          <strong>對於一般投資人，直接持有指數 ETF 的長期績效，普遍優於試圖從成分股中自選自組。</strong>
          DestinyOrder 提供的「成分股隨機抽選」工具，
          並不是要鼓勵你用此取代 ETF，而是提供一個「研究入口」與「打破選股盲點」的輔助。
        </p>
      </section>

      <section class="section">
        <h2>四、隨機抽選的實際應用情境</h2>

        <h3>4.1 突破研究窄化的視野</h3>
        <p>
          對於每天看相同 PTT 看板、相同 YouTube 頻道的投資人，研究池會越來越窄。
          每天讓工具抽出一檔陌生股票，強迫你閱讀其產業、財報與商業模式，
          長期下來，你會建立一個遠比同溫層內部討論更廣的市場認知地圖。
        </p>

        <h3>4.2 對抗 Confirmation Bias</h3>
        <p>
          人類心理學的研究顯示，當我們已經對某檔股票形成偏好（無論是正面或負面），
          我們會無意識地篩選對自己有利的資訊。
          <strong>隨機抽選的工具強迫你接觸「沒有預設立場」的標的，這對培養客觀分析能力極為有益。</strong>
        </p>

        <h3>4.3 建立每日研究習慣</h3>
        <p>
          投資能力的累積靠的是長期、規律的研究習慣，而非偶發的「神來一筆」。
          DestinyOrder 每次抽選只需要 0.1 秒，但它可以變成你每天早上的儀式：
          抽一檔、花 30 分鐘看年報，一年下來你會研究過 365 檔股票，
          這已經是相當少數散戶能長期維持的研究密度。
        </p>

        <h3>4.4 投資組合的隨機分散驗證</h3>
        <p>
          部分研究指出，若候選池本身已具備高度品質與分散性，
          從中隨機抽樣形成的投資組合，其長期表現可能與大盤指數接近。
          這背後的原因通常與等權重效應、小型股傾斜等技術性因素有關，
          並非「隨機本身具備擊敗市場的能力」。
          這個觀察仍然支持一個樸素的結論：
          <strong>分散性 + 合理候選池，本身就是一種低成本的有效策略。</strong>
          DestinyOrder 的多次抽選，可以作為這種「隨機分散」研究的入口。
        </p>
      </section>

      <section class="section">
        <h2>五、為什麼做成「抽抽樂」與「拉霸機」？工具設計哲學</h2>
        <p>
          一個常見的問題是：「為什麼做成這麼浮誇的視覺？」
          答案在於行為經濟學的洞察——
          <strong>人類大腦對「隨機獎勵」的多巴胺反應，遠強於對「理性決策」的滿足感。</strong>
        </p>
        <p>
          這套視覺語言（霓虹燈、跑馬燈、骰子聲、JACKPOT 飛字）借鑑了
          <strong>遊戲化（gamification）與隨機獎勵設計</strong>的概念，
          目的是讓「研究選股」這個本質枯燥的行為，產生類似輕度娛樂的多巴胺回饋。
        </p>
        <p>
          這個設計選擇是有意識的：DestinyOrder 引入遊戲化機制，
          <strong>不是為了刺激你交易，而是為了讓你「願意每天打開研究股票」。</strong>
          抽完之後到底要不要研究、要不要買進，依然取決於你冷靜的判斷。
          這也是為什麼網站底部固定常駐免責聲明——
          我們希望你享受過程，但不希望你混淆了「娛樂」與「投資決策」的界線。
        </p>
      </section>

      <section class="section">
        <h2>六、局限性與誠實的免責</h2>
        <p>本工具的局限性必須被清楚揭示：</p>
        <ul>
          <li>
            <strong>不是投資建議：</strong>隨機抽選不具備任何選股 alpha，
            它只是一個「打破選股盲點」的研究入口，不構成買進或賣出建議。
          </li>
          <li>
            <strong>資料可能延遲：</strong>各 ETF 成分股與權重資料由程式自動從官方來源抓取，
            但因官方更新時程與系統延遲，無法保證即時。
          </li>
          <li>
            <strong>權重不等於價值：</strong>權重高的股票只代表市值大，不代表它一定值得買；
            權重低的股票也不代表沒有潛力。
          </li>
          <li>
            <strong>歷史不代表未來：</strong>所有基於歷史資料的隨機分散研究，
            其結論在未來市場結構性變化時都可能失效。
          </li>
        </ul>
      </section>

      <section class="section">
        <h2>七、五檔候選 ETF 簡介</h2>
        <dl class="etf-list">
          <dt>0050 元大台灣 50（被動 · 市值型）</dt>
          <dd>
            台灣第一檔、也是最具代表性的市值型 ETF，由元大投信發行，
            追蹤「臺灣 50 指數」，涵蓋台股市值前 50 大公司，被視為台股核心資產配置的重要代表。
          </dd>

          <dt>006208 富邦台 50（被動 · 市值型）</dt>
          <dd>
            由富邦投信發行，追蹤與 0050 相同的「臺灣 50 指數」，但長期內扣費用相對較低，
            常被視為 0050 的低成本替代方案，兩者成分股高度重疊。
          </dd>

          <dt>009816 凱基台灣 TOP 50（被動 · 大型股 + 品質篩選 · 不配息）</dt>
          <dd>
            由凱基投信發行，追蹤「臺灣指數公司特選臺灣 TOP 50 指數」。
            選股以台灣大型權值股為核心，但除市值條件外，
            也要求成分股近四季稅後純益為正，因此較偏向「大型股 + 品質篩選」設計。
            最大特色是<strong>不配息、將股息自動再投資</strong>，主打長期複利累積效果。
          </dd>

          <dt>00403A 統一台股升級 50 主動式 ETF（主動式股票 ETF）</dt>
          <dd>
            由統一投信發行的主動式股票 ETF（代號第六碼 A 代表 Active），
            於 2026 年 5 月掛牌上市。不追蹤特定指數，投資策略以大型權值股為核心，
            並從台股市值前段企業中進行主動選股與汰弱留強，
            強調在市值型架構上加入主動投資判斷，被市場稱為「升級版 0050」。
          </dd>

          <dt>00981A 統一台股增長主動式 ETF（主動式股票 ETF）</dt>
          <dd>
            同樣由統一投信發行的主動式股票 ETF，於 2025 年掛牌上市。
            投資方向聚焦於台灣大型與成長型企業，
            並透過主動選股尋找具創新能力與長期成長潛力的公司，
            提供有別於傳統被動市值型 ETF 的投資視角。
          </dd>
        </dl>
      </section>

      <section class="section">
        <h2>八、結語：誠實面對市場的隨機性</h2>
        <p>
          DestinyOrder 不會讓你變成投資大師，但它希望成為你研究路上的一個小工具——
          一個提醒你「市場本來就帶有強烈隨機性、不必過度焦慮選股能力」的小工具；
          一個讓你「每天有理由打開一檔陌生股票去研究」的小工具；
          一個用拉斯維加斯式的視覺，幫你把投資研究這件嚴肅的事，變得稍微好玩一點點的小工具。
        </p>
        <p>
          如果你看完這篇還是想直接買 0050 然後長期持有，那也許就是這個工具最高的成就——
          因為它幫你避開了無數個「以為自己能戰勝市場」的昂貴幻覺。
        </p>
        <p class="closing">
          —— DestinyOrder 開發團隊
        </p>
      </section>
    </article>
  </main>
</template>

<style scoped>
.about-page {
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

.about-article {
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
  font-size: clamp(1.6rem, 5vw, 2.6rem);
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 1.3;
  background: linear-gradient(90deg, #fff 0%, #b3b8ff 60%, #7ec8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.lede {
  margin: 0 auto;
  /* 與下方 .section 卡片同寬，視覺上對齊 */
  max-width: 1040px;
  /* 寬度拉開後不再強制置中，文字段落改回常規閱讀左對齊 */
  text-align: left;
  font-size: clamp(0.95rem, 2.7vw, 1.05rem);
  line-height: 1.85;
  color: #b1b6d6;
}

.lede strong {
  color: #e8eaf6;
  font-weight: 700;
}

.section {
  /* 砍到原本 1/3，讓各區塊之間更緊湊 */
  margin-top: clamp(0.7rem, 1.7vw, 1rem);
  padding: clamp(1.2rem, 3vw, 2rem) clamp(1rem, 3vw, 1.8rem);
  background:
    linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.04) 0%,
      rgba(255, 255, 255, 0.015) 100%
    );
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: clamp(14px, 2.4vw, 20px);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.section h2 {
  margin: 0 0 1rem;
  font-size: clamp(1.15rem, 3.4vw, 1.5rem);
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #f0f2ff;
  border-left: 3px solid #7ec8ff;
  padding-left: 0.8rem;
  line-height: 1.4;
}

.section h3 {
  margin: 1.6rem 0 0.6rem;
  font-size: clamp(1rem, 2.9vw, 1.15rem);
  font-weight: 700;
  color: #b3b8ff;
  letter-spacing: 0.02em;
}

.section h3:first-of-type {
  margin-top: 1.2rem;
}

.section p {
  margin: 0 0 1rem;
  font-size: clamp(0.9rem, 2.6vw, 0.98rem);
  line-height: 1.85;
  color: #c9cce8;
}

.section p strong {
  color: #f0f2ff;
  font-weight: 700;
  background: linear-gradient(
    180deg,
    transparent 60%,
    rgba(126, 200, 255, 0.18) 60%
  );
  padding: 0 2px;
}

.section ul,
.section ol {
  margin: 0 0 1.2rem;
  padding-left: 1.4rem;
  font-size: clamp(0.9rem, 2.6vw, 0.96rem);
  line-height: 1.85;
  color: #c9cce8;
}

.section li {
  margin-bottom: 0.5rem;
}

.section li strong {
  color: #f0f2ff;
}

.section blockquote {
  margin: 1rem 0 1.4rem;
  padding: 0.9rem 1.2rem;
  border-left: 3px solid #b3b8ff;
  background: rgba(179, 184, 255, 0.06);
  border-radius: 0 10px 10px 0;
  font-style: italic;
  color: #e2e6ff;
  font-size: clamp(0.92rem, 2.6vw, 1rem);
  line-height: 1.8;
}

.etf-list {
  margin: 1rem 0 0;
  padding: 0;
}

.etf-list dt {
  font-size: clamp(0.95rem, 2.7vw, 1.05rem);
  font-weight: 700;
  color: #b3b8ff;
  margin-top: 1rem;
  letter-spacing: 0.04em;
}

.etf-list dt:first-child {
  margin-top: 0;
}

.etf-list dd {
  margin: 0.3rem 0 0;
  padding-left: 0.8rem;
  border-left: 2px solid rgba(126, 200, 255, 0.3);
  font-size: clamp(0.88rem, 2.5vw, 0.95rem);
  line-height: 1.8;
  color: #c9cce8;
}

.closing {
  margin-top: 1.5rem;
  text-align: right;
  color: #8a8fae;
  font-size: clamp(0.85rem, 2.4vw, 0.92rem);
  letter-spacing: 0.05em;
}

.br-mobile {
  display: none;
}

@media (max-width: 540px) {
  .section {
    padding: 1rem 0.9rem;
  }
  .section h2 {
    font-size: 1.1rem;
    padding-left: 0.6rem;
  }
  .br-mobile {
    display: inline;
  }
}
</style>

import {
  AlertTriangle,
  ArrowRight,
  Camera,
  Check,
  ChefHat,
  Clock3,
  ExternalLink,
  Leaf,
  LoaderCircle,
  MessageCircle,
  Minus,
  Plus,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, analyzeImage, getHealth, recommendRecipes, sendChat } from "./api";
import { type SortMode, sortRecipes } from "./lib/sortRecipes";
import type { Health, Ingredient, Recipe, UserPreferences } from "./types";

type BusyState = "idle" | "analyzing" | "recommending" | "chatting";
type ChatItem = { role: "user" | "assistant"; content: string };

const initialPreferences: UserPreferences = {
  people: 2,
  flavors: [],
  allergies: [],
  dislikes: [],
  max_minutes: 45,
  difficulty: "适中",
};

const splitTags = (value: string) =>
  value
    .split(/[，,、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [note, setNote] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [uncertainItems, setUncertainItems] = useState<string[]>([]);
  const [analysisNotes, setAnalysisNotes] = useState("");
  const [preferences, setPreferences] = useState<UserPreferences>(initialPreferences);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [notice, setNotice] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("score");
  const [expandedRecipe, setExpandedRecipe] = useState("");
  const [busy, setBusy] = useState<BusyState>("idle");
  const [error, setError] = useState("");
  const [chat, setChat] = useState<ChatItem[]>([
    { role: "assistant", content: "等菜谱生成后，可以问我替换食材、调整份量或某一步怎么做。" },
  ]);
  const [chatInput, setChatInput] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const sortedRecipes = useMemo(() => sortRecipes(recipes, sortMode), [recipes, sortMode]);
  const currentStep = recipes.length ? 3 : ingredients.length ? 2 : file ? 1 : 0;

  function selectFile(nextFile: File | undefined) {
    if (!nextFile) return;
    if (!(["image/jpeg", "image/png", "image/webp"].includes(nextFile.type))) {
      setError("请选择 JPG、PNG 或 WebP 图片。");
      return;
    }
    if (nextFile.size > 10 * 1024 * 1024) {
      setError("图片不能超过 10 MB。");
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(nextFile);
    setPreviewUrl(URL.createObjectURL(nextFile));
    setIngredients([]);
    setRecipes([]);
    setSessionId("");
    setError("");
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  }

  async function runAnalysis() {
    if (!file) {
      setError("请先选择一张食材图片。");
      return;
    }
    setBusy("analyzing");
    setError("");
    try {
      const result = await analyzeImage(file, note);
      setSessionId(result.session_id);
      setIngredients(result.ingredients);
      setUncertainItems(result.uncertain_items);
      setAnalysisNotes(result.notes);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "识别失败，请稍后重试。");
    } finally {
      setBusy("idle");
    }
  }

  function updateIngredient(index: number, patch: Partial<Ingredient>) {
    setIngredients((items) => items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  function addIngredient() {
    setIngredients((items) => [
      ...items,
      { name: "", normalized_name: "", amount: "适量", confidence: 1, source: "user" },
    ]);
  }

  async function runRecommendation() {
    const validIngredients = ingredients.filter((item) => item.name.trim());
    if (!sessionId || !validIngredients.length) {
      setError("请先完成食材识别，并至少保留一种食材。");
      return;
    }
    setBusy("recommending");
    setError("");
    try {
      const result = await recommendRecipes(sessionId, validIngredients, preferences);
      setRecipes(result.recipes);
      setNotice(result.notice);
      setExpandedRecipe(result.recipes[0]?.id ?? "");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "推荐失败，请稍后重试。");
    } finally {
      setBusy("idle");
    }
  }

  async function submitChat(event: FormEvent) {
    event.preventDefault();
    const message = chatInput.trim();
    if (!message || !sessionId || busy !== "idle") return;
    setChat((items) => [...items, { role: "user", content: message }]);
    setChatInput("");
    setBusy("chatting");
    try {
      const answer = await sendChat(sessionId, message);
      setChat((items) => [...items, { role: "assistant", content: answer }]);
    } catch (caught) {
      setChat((items) => [
        ...items,
        { role: "assistant", content: caught instanceof ApiError ? caught.message : "暂时无法回答。" },
      ]);
    } finally {
      setBusy("idle");
    }
  }

  function resetAll() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl("");
    setNote("");
    setSessionId("");
    setIngredients([]);
    setUncertainItems([]);
    setAnalysisNotes("");
    setPreferences(initialPreferences);
    setRecipes([]);
    setNotice("");
    setError("");
    setChat([{ role: "assistant", content: "等菜谱生成后，可以问我替换食材、调整份量或某一步怎么做。" }]);
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <header className="topbar">
        <a className="brand" href="#top" aria-label="灶边 AI 首页">
          <span className="brand-mark"><ChefHat size={22} /></span>
          <span><b>灶边 AI</b><small>你的私厨管家</small></span>
        </a>
        <div className="status-cluster">
          <span className={`status-dot ${health?.model_configured ? "online" : "offline"}`} />
          <span>{health?.model_configured ? `${health.model} 已就绪` : "等待模型配置"}</span>
          <button className="ghost-button" onClick={resetAll}><RotateCcw size={15} /> 新会话</button>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="eyebrow"><Sparkles size={15} /> 看看冰箱，今晚就有答案</div>
          <h1>把现有食材，<em>变成一桌好菜。</em></h1>
          <p>拍下冰箱或厨房里的食材，AI 识别后按你的口味、时间和难度，给出真正能下厨的菜谱。</p>
          <div className="steps" aria-label="使用步骤">
            {["上传照片", "确认食材", "设置偏好", "开始下厨"].map((label, index) => (
              <div className={`step ${currentStep >= index ? "active" : ""}`} key={label}>
                <span>{currentStep > index ? <Check size={14} /> : index + 1}</span>{label}
              </div>
            ))}
          </div>
        </section>

        {error && <div className="error-banner"><AlertTriangle size={18} /><span>{error}</span><button onClick={() => setError("")}><X size={16} /></button></div>}

        <section className="workspace-grid">
          <div className="control-column">
            <article className="panel upload-panel">
              <div className="panel-heading">
                <div><span className="section-number">01</span><h2>给我看一眼食材</h2></div>
                <span className="soft-label">单张 · 最大 10 MB</span>
              </div>
              <div
                className={`dropzone ${previewUrl ? "has-image" : ""}`}
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInput.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => event.key === "Enter" && fileInput.current?.click()}
              >
                <input
                  ref={fileInput}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  hidden
                  onChange={(event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0])}
                />
                {previewUrl ? (
                  <><img src={previewUrl} alt="待识别食材预览" /><div className="image-overlay"><Camera size={18} /> 点击更换图片</div></>
                ) : (
                  <div className="dropzone-empty"><span><Camera size={28} /></span><b>拖入食材照片</b><p>或点击从电脑选择</p><small>支持 JPG · PNG · WebP</small></div>
                )}
              </div>
              <label className="field-label" htmlFor="note">补充说明 <span>可选</span></label>
              <textarea id="note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="例如：左下角盒子里是豆腐，调料不用识别…" rows={2} />
              <button className="primary-button wide" onClick={runAnalysis} disabled={!file || busy !== "idle"}>
                {busy === "analyzing" ? <><LoaderCircle className="spin" size={18} /> 正在看图识材…</> : <><Sparkles size={18} /> 识别食材 <ArrowRight size={17} /></>}
              </button>
            </article>

            {ingredients.length > 0 && (
              <article className="panel ingredient-panel">
                <div className="panel-heading"><div><span className="section-number">02</span><h2>确认识别结果</h2></div><span className="soft-label green">{ingredients.length} 种食材</span></div>
                {(analysisNotes || uncertainItems.length > 0) && (
                  <div className="analysis-note"><Search size={16} /><span>{analysisNotes || `这些项目需要确认：${uncertainItems.join("、")}`}</span></div>
                )}
                <div className="ingredient-list">
                  {ingredients.map((item, index) => (
                    <div className="ingredient-row" key={`${index}-${item.name}`}>
                      <div className="ingredient-index">{String(index + 1).padStart(2, "0")}</div>
                      <input aria-label={`食材 ${index + 1} 名称`} value={item.name} placeholder="食材名称" onChange={(event) => updateIngredient(index, { name: event.target.value, normalized_name: event.target.value })} />
                      <input className="amount-input" aria-label={`食材 ${index + 1} 数量`} value={item.amount} placeholder="数量" onChange={(event) => updateIngredient(index, { amount: event.target.value })} />
                      <span className={`confidence ${item.confidence >= 0.75 ? "high" : "low"}`}>{Math.round(item.confidence * 100)}%</span>
                      <button className="icon-button danger" aria-label={`删除 ${item.name}`} onClick={() => setIngredients((items) => items.filter((_, i) => i !== index))}><Trash2 size={16} /></button>
                    </div>
                  ))}
                </div>
                <button className="add-button" onClick={addIngredient}><Plus size={16} /> 手动添加食材</button>
              </article>
            )}

            {ingredients.length > 0 && (
              <article className="panel preference-panel">
                <div className="panel-heading"><div><span className="section-number">03</span><h2>今天想怎么吃</h2></div></div>
                <div className="form-grid">
                  <div className="form-field"><label><Users size={15} /> 用餐人数</label><div className="counter"><button onClick={() => setPreferences((p) => ({ ...p, people: Math.max(1, p.people - 1) }))}><Minus size={14} /></button><b>{preferences.people}</b><button onClick={() => setPreferences((p) => ({ ...p, people: Math.min(12, p.people + 1) }))}><Plus size={14} /></button></div></div>
                  <div className="form-field"><label><Clock3 size={15} /> 最长用时</label><select value={preferences.max_minutes} onChange={(e) => setPreferences((p) => ({ ...p, max_minutes: Number(e.target.value) }))}><option value={20}>20 分钟</option><option value={30}>30 分钟</option><option value={45}>45 分钟</option><option value={60}>60 分钟</option><option value={90}>90 分钟</option></select></div>
                  <div className="form-field full"><label><ChefHat size={15} /> 难度</label><div className="segmented">{(["简单", "适中", "进阶"] as const).map((level) => <button className={preferences.difficulty === level ? "selected" : ""} key={level} onClick={() => setPreferences((p) => ({ ...p, difficulty: level }))}>{level}</button>)}</div></div>
                  <div className="form-field full"><label><Leaf size={15} /> 口味偏好</label><input placeholder="清淡、香辣、酸甜（用逗号分隔）" onChange={(e) => setPreferences((p) => ({ ...p, flavors: splitTags(e.target.value) }))} /></div>
                  <div className="form-field full warning-field"><label><ShieldCheck size={15} /> 过敏原 <small>绝对排除</small></label><input placeholder="例如：花生、虾、牛奶" onChange={(e) => setPreferences((p) => ({ ...p, allergies: splitTags(e.target.value) }))} /></div>
                  <div className="form-field full"><label>普通忌口</label><input placeholder="例如：香菜、肥肉" onChange={(e) => setPreferences((p) => ({ ...p, dislikes: splitTags(e.target.value) }))} /></div>
                </div>
                <button className="primary-button wide" onClick={runRecommendation} disabled={busy !== "idle"}>
                  {busy === "recommending" ? <><LoaderCircle className="spin" size={18} /> 正在搜寻并搭配…</> : <><ChefHat size={18} /> 生成我的菜单 <ArrowRight size={17} /></>}
                </button>
                <p className="safety-copy"><ShieldCheck size={13} /> 过敏信息会作为硬性限制，但烹饪前仍请核对食品标签。</p>
              </article>
            )}
          </div>

          <div className="result-column">
            {recipes.length === 0 ? (
              <article className="empty-result">
                <div className="plate-illustration"><span className="plate-ring" /><Leaf size={30} /><Sparkles className="plate-spark" size={20} /></div>
                <p className="result-kicker">YOUR PERSONAL MENU</p>
                <h2>好菜单，从看见食材开始</h2>
                <p>上传一张照片，确认识别结果，再告诉我今天的用餐偏好。你的专属菜单会出现在这里。</p>
                <div className="promise-list"><span><Check size={14} /> 优先用完现有食材</span><span><Check size={14} /> 按时间和难度排序</span><span><Check size={14} /> 标清缺少的配料</span></div>
              </article>
            ) : (
              <>
                <div className="results-header">
                  <div><span className="result-kicker">YOUR PERSONAL MENU</span><h2>为你挑出的 {recipes.length} 道菜</h2><p>{notice}</p></div>
                  <select aria-label="菜谱排序" value={sortMode} onChange={(e) => setSortMode(e.target.value as SortMode)}><option value="score">综合推荐</option><option value="coverage">食材利用最高</option><option value="fast">用时最短</option><option value="easy">难度最低</option></select>
                </div>
                <div className="recipe-list">
                  {sortedRecipes.map((recipe, index) => {
                    const expanded = expandedRecipe === recipe.id;
                    return (
                      <article className={`recipe-card ${expanded ? "expanded" : ""}`} key={recipe.id}>
                        <button className="recipe-summary" onClick={() => setExpandedRecipe(expanded ? "" : recipe.id)}>
                          <div className="rank">{String(index + 1).padStart(2, "0")}</div>
                          <div className="recipe-main"><div className="recipe-title-row"><h3>{recipe.title}</h3><span className="score-badge">{recipe.score}<small>分</small></span></div><p>{recipe.summary}</p><div className="recipe-meta"><span><Clock3 size={14} /> {recipe.total_minutes} 分钟</span><span><ChefHat size={14} /> {recipe.difficulty}</span><span><Users size={14} /> {recipe.servings} 人份</span>{recipe.source_type === "ai_with_web" && <span className="web-tag"><ExternalLink size={13} /> 网络参考</span>}</div><div className="reason-row">{recipe.score_reasons.map((reason) => <span key={reason}>{reason}</span>)}</div></div>
                          <span className="expand-icon">{expanded ? <Minus size={18} /> : <Plus size={18} />}</span>
                        </button>
                        {expanded && (
                          <div className="recipe-detail">
                            <div className="detail-grid">
                              <div><h4>用料清单</h4><ul className="ingredient-checklist">{recipe.ingredients.map((item) => <li key={`${item.name}-${item.amount}`}><Check size={13} /><span>{item.name}</span><b>{item.amount}</b></li>)}</ul>{recipe.missing_ingredients.length > 0 && <div className="missing-box"><b>还需准备</b><span>{recipe.missing_ingredients.join(" · ")}</span></div>}</div>
                              <div><h4>烹饪步骤</h4><ol className="cooking-steps">{recipe.steps.map((step, i) => <li key={step}><span>{i + 1}</span><p>{step}</p></li>)}</ol></div>
                            </div>
                            <div className="nutrition-box"><Leaf size={17} /><div><b>营养搭配提示</b><p>{recipe.nutrition_summary}</p></div></div>
                            {recipe.sources.length > 0 && <div className="sources"><b>参考资料</b>{recipe.sources.map((source) => <a href={source.url} target="_blank" rel="noreferrer" key={source.url}>{source.title}<ExternalLink size={12} /></a>)}</div>}
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              </>
            )}

            <article className={`chat-panel ${recipes.length ? "ready" : ""}`}>
              <div className="chat-heading"><div><span><MessageCircle size={18} /></span><div><h3>问问私厨管家</h3><small>{recipes.length ? "已读懂本次菜单" : "生成菜单后开启上下文问答"}</small></div></div><span className="ai-dot">AI</span></div>
              <div className="chat-messages">{chat.map((item, index) => <div className={`chat-message ${item.role}`} key={`${index}-${item.content.slice(0, 8)}`}>{item.content}</div>)}{busy === "chatting" && <div className="chat-message assistant typing"><i /><i /><i /></div>}</div>
              <form className="chat-form" onSubmit={submitChat}><input value={chatInput} onChange={(e) => setChatInput(e.target.value)} disabled={!recipes.length} placeholder={recipes.length ? "例如：没有料酒，可以用什么替代？" : "请先生成菜单"} /><button disabled={!recipes.length || !chatInput.trim() || busy !== "idle"} aria-label="发送"><Send size={17} /></button></form>
              <p className="chat-disclaimer">建议仅供日常烹饪参考，过敏与健康问题请以专业意见为准。</p>
            </article>
          </div>
        </section>
      </main>
      <footer><span>灶边 AI · 让每一种食材都有去处</span><span>LangChain × {health?.model ?? "Qwen"}</span></footer>
    </div>
  );
}

export default App;


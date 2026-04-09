import { useEffect, useRef, useState } from "react";
import CRTTvShell from "./CRTTvShell.jsx";

const TASKS = [
  {
    id: "clinical_calc",
    label: "Clinical Calc",
    difficulty: "easy",
    description: "Compute a clinical metric from a patient note and print the result.",
  },
  {
    id: "biostat_power",
    label: "Biostat Power",
    difficulty: "medium",
    description: "Solve a sample size or power analysis problem with executable Python.",
  },
  {
    id: "biocoder",
    label: "BioCoder",
    difficulty: "hard",
    description: "Implement a biomedical Python function body from a specification.",
  },
];

function getRewardTone(reward) {
  if (reward === null || reward === undefined) return "neutral";
  if (reward >= 1) return "strong";
  if (reward >= 0.5) return "good";
  if (reward > 0) return "weak";
  return "bad";
}

function TerminalTyper({ text, speed = 55 }) {
  const [displayed, setDisplayed] = useState("");
  const [cursorOn, setCursorOn] = useState(true);

  useEffect(() => {
    let i = 0;
    setDisplayed("");
    const timer = setInterval(() => {
      i += 1;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(timer);
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);

  useEffect(() => {
    const blink = setInterval(() => setCursorOn((value) => !value), 530);
    return () => clearInterval(blink);
  }, []);

  return (
    <span>
      {displayed}
      <span className={`termCursor ${cursorOn ? "on" : ""}`}>|</span>
    </span>
  );
}

function CollapsibleSection({ title, content, defaultExpanded = false, hideHint, onInteract }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  function handleToggle() {
    setExpanded((value) => !value);
    onInteract?.();
  }

  return (
    <div className="probSection">
      <div className="probSectionHeaderRow">
        <button className="probSectionHeader" onClick={handleToggle} type="button">
          <span className="probSectionArrow">{expanded ? "v" : ">"}</span>
          <span className="probSectionTitleText">{title}</span>
        </button>
        {!hideHint && (
          <span className="probSectionHint">
            {expanded ? "(click to collapse)" : "(click to expand)"}
          </span>
        )}
      </div>
      {expanded && <pre className="probSectionContent">{content}</pre>}
    </div>
  );
}

function FormattedProblemStatement({ text, hideHint, onInteract }) {
  if (!text) return <div className="problemTextFormatted">No episode loaded yet.</div>;

  const parts = text.split("---");
  const sections = [];
  const intro = parts[0].trim();

  if (intro) {
    sections.push({ title: "PRESUMPTION", content: intro });
  }

  for (let i = 1; i < parts.length; i += 2) {
    const title = parts[i].trim();
    const content = (parts[i + 1] || "").trim();
    sections.push({ title, content });
  }

  return (
    <div className="problemTextFormatted">
      {sections.map((section, index) => {
        const isQuestion =
          section.title.includes("QUESTION") ||
          section.title.includes("PROBLEM") ||
          section.title.includes("DESCRIPTION");

        return (
          <CollapsibleSection
            key={`${section.title}-${index}`}
            title={section.title}
            content={section.content}
            defaultExpanded={isQuestion}
            hideHint={hideHint}
            onInteract={onInteract}
          />
        );
      })}
    </div>
  );
}

function LineTypingTerminal({ text }) {
  const [visibleLines, setVisibleLines] = useState(0);
  const lines = text ? text.split("\n") : [];

  useEffect(() => {
    setVisibleLines(0);
    if (!text) return undefined;

    const interval = setInterval(() => {
      setVisibleLines((value) => {
        if (value < lines.length) return value + 1;
        clearInterval(interval);
        return value;
      });
    }, 40);

    return () => clearInterval(interval);
  }, [lines.length, text]);

  if (!text) {
    return <div className="retroTerminalLine">LLM/response&gt; awaiting output</div>;
  }

  return (
    <div className="blackTerminalWindow">
      {lines.slice(0, visibleLines).map((line, index) => (
        <div key={`${index}-${line}`} className="retroTerminalLine">
          LLM/response&gt; {line || " "}
        </div>
      ))}
      {visibleLines < lines.length && (
        <div className="retroTerminalLine termCursor on">LLM/response&gt; _</div>
      )}
    </div>
  );
}

function IntroScreen({ onStart, leaving }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const startButtonRef = useRef(null);

  useEffect(() => {
    function handleKeyDown(event) {
      if (leaving) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, TASKS.length - 1));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (event.key === "Enter") {
        event.preventDefault();
        if (startButtonRef.current) {
          startButtonRef.current.click();
        } else {
          onStart(TASKS[selectedIndex].id);
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [leaving, onStart, selectedIndex]);

  return (
    <div className={`introScreen${leaving ? " leaving" : ""}`}>
      <div className="introInner">
        <p className="terminalPrompt retroHeadingText titlePrompt">
          <TerminalTyper text="> Clinical Bench" />
        </p>

        <article className="panel retroPanel introDifficultyPanel">
          <div className="retroHeadingBar">
            <h2 className="retroHeadingText">CHOOSE DIFFICULTY</h2>
          </div>

          <div className="taskSelectList">
            {TASKS.map((task, index) => {
              const isSelected = selectedIndex === index;
              return (
                <div key={task.id} className={`taskSelectRow${isSelected ? " open" : ""}`}>
                  <button
                    className={`taskSelectBtn${isSelected ? " active" : ""}`}
                    onClick={() => setSelectedIndex(index)}
                    type="button"
                  >
                    <span className="tsChevron">&gt;</span>
                    <span className="tsDiff">{task.difficulty.toUpperCase()}</span>
                    <span className="tsDot">•</span>
                    <span className="tsLabel">{task.label}</span>
                  </button>
                  {isSelected && (
                    <p className="tsDesc">
                      <TerminalTyper text={task.description} speed={25} />
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          <div className="startBtnWrap">
            <button
              ref={startButtonRef}
              className="pixelStartBtn introStartBtn"
              onClick={() => onStart(TASKS[selectedIndex].id)}
              type="button"
            >
              START
            </button>
          </div>
        </article>
      </div>
    </div>
  );
}

function PauseMenu({ onResume, onChangeDifficulty, onExit }) {
  return (
    <div className="pauseOverlay">
      <div className="pauseMenu">
        <div className="pauseTitle">PAUSED</div>
        <div className="pauseItems">
          <button className="pixelStartBtn pauseItem" onClick={onResume} type="button">
            RESUME
          </button>
          <button className="pixelStartBtn pauseItem" onClick={onChangeDifficulty} type="button">
            CHANGE DIFFICULTY
          </button>
          <button className="pixelStartBtn pauseItem pauseItem--exit" onClick={onExit} type="button">
            EXIT
          </button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [gamePhase, setGamePhase] = useState("intro");
  const [introLeaving, setIntroLeaving] = useState(false);
  const [taskName, setTaskName] = useState("clinical_calc");
  const [sessionId, setSessionId] = useState(null);
  const [taskDescription, setTaskDescription] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [maxSteps, setMaxSteps] = useState(8);
  const [steps, setSteps] = useState([]);
  const [selectedStepId, setSelectedStepId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [hasInteractedWithCollapse, setHasInteractedWithCollapse] = useState(false);

  const latest = steps[steps.length - 1] ?? null;
  const displayStep = steps.find((step) => step.id === selectedStepId) ?? latest;
  const rewardTone = getRewardTone(displayStep?.reward ?? null);
  const isActive = Boolean(sessionId) && !done;
  const totalReward = steps.reduce((sum, step) => sum + (step.reward ?? 0), 0);
  const currentDifficulty = difficulty || "unrated";
  const isHistoricalView =
    selectedStepId !== null &&
    steps.length > 0 &&
    selectedStepId !== steps[steps.length - 1].id;

  function clearEpisodeState() {
    setSessionId(null);
    setSteps([]);
    setSelectedStepId(null);
    setDone(false);
    setError(null);
    setTaskDescription("");
    setDifficulty("");
    setHistoryOpen(false);
    setHasInteractedWithCollapse(false);
  }

  async function startEpisode(nameOverride) {
    const name = nameOverride ?? taskName;
    setLoading(true);
    setError(null);
    setSteps([]);
    setSelectedStepId(null);
    setDone(false);
    setSessionId(null);
    setTaskDescription("");
    setDifficulty("");
    setHistoryOpen(false);
    setHasInteractedWithCollapse(false);

    try {
      const response = await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_name: name, seed: 42 }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Reset failed (${response.status})`);
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setTaskDescription(data.task_description);
      setDifficulty(data.difficulty);
      setMaxSteps(data.max_steps);
      setTaskName(data.task_name || name);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleIntroStart(selectedId) {
    setTaskName(selectedId);
    setIntroLeaving(true);
    await new Promise((resolve) => setTimeout(resolve, 520));
    setGamePhase("playing");
    setIntroLeaving(false);
    await startEpisode(selectedId);
  }

  function handlePause() {
    setGamePhase("paused");
  }

  function handleResume() {
    setGamePhase("playing");
  }

  function handleChangeDifficulty() {
    clearEpisodeState();
    setGamePhase("intro");
  }

  function handleExit() {
    clearEpisodeState();
    setGamePhase("intro");
  }

  async function nextStep() {
    if (!sessionId || loading || done) return;
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/ai-step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Step failed (${response.status})`);
      }

      const data = await response.json();
      const newStep = { ...data, id: crypto.randomUUID() };

      setSteps((prev) => [...prev, newStep]);
      setSelectedStepId(newStep.id);

      if (data.done) {
        setDone(true);
        setSessionId(null);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  function handleNextOrPresent() {
    if (isHistoricalView && latest) {
      setSelectedStepId(latest.id);
      return;
    }
    nextStep();
  }

  return (
    <CRTTvShell>
      {gamePhase === "intro" && <IntroScreen onStart={handleIntroStart} leaving={introLeaving} />}

      {gamePhase !== "intro" && (
        <main className="appShell">
          {gamePhase === "paused" && (
            <PauseMenu
              onResume={handleResume}
              onChangeDifficulty={handleChangeDifficulty}
              onExit={handleExit}
            />
          )}

          <section className="topBar">
            <div className="productCopy">
              <h1>&gt; Clinical Bench</h1>
            </div>

            <div className="topBarActions">
              {done && <div className="statusPill">Episode complete</div>}
              {loading && sessionId && (
                <div className="statusPill connecting">
                  <span aria-hidden="true" />
                  AI thinking...
                </div>
              )}
              {taskDescription && !loading && (
                <div className="statusPill connected">
                  <span aria-hidden="true" />
                  {currentDifficulty}
                </div>
              )}
              <button
                className="pixelStartBtn uiActionBtn"
                onClick={() => startEpisode()}
                disabled={loading}
                type="button"
              >
                {loading && !sessionId ? "Starting..." : sessionId || done ? "Restart" : "Start Episode"}
              </button>
              <button className="pixelStartBtn pauseBtn" onClick={handlePause} title="Pause" type="button">
                PAUSE
              </button>
            </div>
          </section>

          <section className="mainGrid">
            <div className="column columnPrimary">
              <article className="panel retroPanel problemPanel">
                <div
                  className="retroHeadingBar"
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
                >
                  <h2 className="retroHeadingText">PROBLEM STATEMENT</h2>
                  <button
                    className="pixelStartBtn uiActionBtn"
                    onClick={handleNextOrPresent}
                    disabled={(!isActive && !isHistoricalView) || loading}
                    type="button"
                    style={{ minWidth: "auto", padding: "0.6rem 1.2rem", fontSize: "0.7rem" }}
                  >
                    {isHistoricalView ? "GO TO LATEST" : loading && sessionId ? "THINKING..." : "NEXT"}
                  </button>
                </div>

                <FormattedProblemStatement
                  text={taskDescription}
                  hideHint={hasInteractedWithCollapse}
                  onInteract={() => setHasInteractedWithCollapse(true)}
                />
              </article>

              <article className="panel retroPanel stepStatePanel">
                <div className="stepStateRow">
                  <div className="stepStateCol">
                    <div className="retroHeadingText stepStateHeading">STEP</div>
                    <strong className="stepStateValue">{displayStep?.step_number ?? 0}</strong>
                  </div>
                  <div className="stepStateCol">
                    <div className="retroHeadingText stepStateHeading">REWARD</div>
                    <strong className={`stepStateValue ${rewardTone}`}>
                      {displayStep?.reward?.toFixed(2) ?? "--"}
                    </strong>
                  </div>
                  <div className="stepStateCol">
                    <div className="retroHeadingText stepStateHeading">STATUS</div>
                    <strong className="stepStateValue">
                      {displayStep
                        ? displayStep.error
                          ? "ERROR"
                          : displayStep.done
                            ? "DONE"
                            : "RUNNING"
                        : "AWAITING"}
                    </strong>
                  </div>
                </div>
              </article>

              <article className="panel retroPanel editorPanel">
                <div className="retroHeadingBar">
                  <h2 className="retroHeadingText">LLM PYTHON RESPONSE</h2>
                </div>
                <LineTypingTerminal text={displayStep?.generated_code} />
              </article>
            </div>

            <div className="column columnSecondary">
              {error && (
                <div className="errorBanner">
                  <span className="blockLabel">Error</span>
                  <span>{error}</span>
                </div>
              )}

              <div className="expandableContainer">
                <button
                  className={`pixelStartBtn uiActionBtn retroToggle ${historyOpen ? "active" : ""}`}
                  onClick={() => setHistoryOpen((value) => !value)}
                  type="button"
                >
                  {historyOpen ? "HIDE HISTORY" : "SHOW HISTORY"}
                </button>

                {historyOpen && (
                  <article className="panel retroPanel expandableContent">
                    <div className="timelineList">
                      {steps.length === 0 ? (
                        <p className="emptyState">No steps yet. Start an episode and click Next.</p>
                      ) : (
                        steps.map((step) => {
                          const stepActive = selectedStepId === step.id;
                          return (
                            <button
                              key={step.id}
                              type="button"
                              className={`probSectionHeader historyItemBtn ${stepActive ? "active" : ""}`}
                              onClick={() => setSelectedStepId(step.id)}
                            >
                              <span className="probSectionTitleText">STEP {step.step_number}</span>
                              <span
                                className={`rewardValue ${getRewardTone(step.reward)}`}
                                style={{ marginLeft: "auto", marginRight: "1rem", fontSize: "0.6rem" }}
                              >
                                {step.reward?.toFixed(2) ?? "--"}
                              </span>
                              <span
                                className="probSectionTitleText"
                                style={{ color: step.error ? "#ff4d4d" : "inherit" }}
                              >
                                {step.error ? "ERROR" : step.done ? "DONE" : "OK"}
                              </span>
                            </button>
                          );
                        })
                      )}
                    </div>
                  </article>
                )}
              </div>

              {displayStep?.metadata && (
                <article className="panel retroPanel scorePanel">
                  <div className="retroHeadingBar">
                    <h2 className="retroHeadingText">METADATA</h2>
                  </div>
                  <div className="statList">
                    {Object.entries(displayStep.metadata).map(([key, value]) => (
                      <div className="statListRow" key={key}>
                        <span className="statListLabel retroFontWhite">{key.replace(/_/g, " ")}</span>
                        <strong className="rewardValue neutral">{String(value)}</strong>
                      </div>
                    ))}
                  </div>
                </article>
              )}

              <article className="panel retroPanel scorePanel">
                <div className="retroHeadingBar">
                  <h2 className="retroHeadingText">EPISODE STATISTICS</h2>
                </div>

                <div className="statList">
                  <div className="statListRow">
                    <span className="statListLabel retroFontWhite">LAST REWARD</span>
                    <strong className={`rewardValue ${rewardTone}`}>
                      {displayStep?.reward?.toFixed(2) ?? "--"}
                    </strong>
                  </div>
                  <div className="statListRow">
                    <span className="statListLabel retroFontWhite">TOTAL REWARD</span>
                    <strong className="rewardValue neutral">{totalReward.toFixed(2)}</strong>
                  </div>
                  <div className="statListRow">
                    <span className="statListLabel retroFontWhite">STEP</span>
                    <strong className="rewardValue neutral">
                      {displayStep?.step_number ?? 0} / {displayStep?.max_steps ?? maxSteps}
                    </strong>
                  </div>
                  <div className="statListRow">
                    <span className="statListLabel retroFontWhite">STATUS</span>
                    <strong className="rewardValue neutral">
                      {done ? "Complete" : isActive ? "Running" : "Idle"}
                    </strong>
                  </div>
                </div>
              </article>

              <article className="panel retroPanel scorePanel">
                <div className="retroHeadingBar">
                  <h2 className="retroHeadingText">STEP FEEDBACK</h2>
                </div>
                <div className="statList">
                  <div className="statListRow">
                    <span className="statListLabel retroFontWhite">EXECUTION RESULT</span>
                    <strong className="rewardValue neutral feedbackValue">
                      {displayStep?.execution_result || "No execution output yet."}
                    </strong>
                  </div>
                  <div className="statListRow">
                    <span className="statListLabel retroFontWhite">ERROR</span>
                    <strong className={`rewardValue feedbackValue ${displayStep?.error ? "bad" : "neutral"}`}>
                      {displayStep?.error || "None"}
                    </strong>
                  </div>
                </div>
              </article>
            </div>
          </section>
        </main>
      )}
    </CRTTvShell>
  );
}

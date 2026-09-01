/**
 * InterviewIQ Pro - Client Application Logic
 * RAG AI Interview & Scorecard System
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // State
  const state = {
    resumeId: null,
    sessionId: null,
    currentQuestionIndex: 1,
    totalQuestions: 5,
    activeQuestion: null,
    timerInterval: null,
    secondsElapsed: 0,
    isRecording: false,
    recognition: null
  };

  // Elements
  const stageSetup = document.getElementById('stage-setup');
  const stageInterview = document.getElementById('stage-interview');
  const stageScorecard = document.getElementById('stage-scorecard');
  const btnResetApp = document.getElementById('btn-reset-app');

  // Stage 1 Elements
  const dropzone = document.getElementById('dropzone');
  const resumeFileInput = document.getElementById('resume-file-input');
  const dropzoneContent = document.getElementById('dropzone-content');
  const uploadSpinner = document.getElementById('upload-spinner');
  const uploadSuccess = document.getElementById('upload-success');
  const uploadedFilename = document.getElementById('uploaded-filename');
  const uploadedMeta = document.getElementById('uploaded-meta');
  const btnReupload = document.getElementById('btn-reupload');
  const sectionsPreview = document.getElementById('sections-preview');
  const detectedTags = document.getElementById('detected-tags');
  const interviewConfigForm = document.getElementById('interview-config-form');
  const btnStartInterview = document.getElementById('btn-start-interview');
  const ctaHint = document.getElementById('cta-hint');
  const targetRoleInput = document.getElementById('target-role');
  const rolePills = document.querySelectorAll('.role-pill');

  // Stage 2 Elements
  const currentQNum = document.getElementById('current-q-num');
  const totalQNum = document.getElementById('total-q-num');
  const questionCategory = document.getElementById('question-category');
  const interviewProgressFill = document.getElementById('interview-progress-fill');
  const interviewTimer = document.getElementById('interview-timer');
  const activeQuestionText = document.getElementById('active-question-text');
  const activeResumeContext = document.getElementById('active-resume-context');
  const answerInput = document.getElementById('answer-input');
  const wordCount = document.getElementById('word-count');
  const btnVoiceInput = document.getElementById('btn-voice-input');
  const micStatusText = document.getElementById('mic-status-text');
  const btnSubmitAnswer = document.getElementById('btn-submit-answer');
  const submitBtnText = document.getElementById('submit-btn-text');
  const btnSkipQuestion = document.getElementById('btn-skip-question');

  // Real-time Evaluation Drawer
  const evaluationDrawer = document.getElementById('evaluation-drawer');
  const evalStatusBadge = document.getElementById('eval-status-badge');
  const evalScoreNum = document.getElementById('eval-score-num');
  const evalFeedback = document.getElementById('eval-feedback');
  const evalStrengthsList = document.getElementById('eval-strengths-list');
  const evalImprovementsList = document.getElementById('eval-improvements-list');
  const evalIdealAnswer = document.getElementById('eval-ideal-answer');
  const btnNextQuestion = document.getElementById('btn-next-question');
  const nextQText = document.getElementById('next-q-text');
  const btnCloseEval = document.getElementById('btn-close-eval');

  // Stage 3 Elements (Scorecard)
  const scorecardRole = document.getElementById('scorecard-role');
  const scorecardDifficulty = document.getElementById('scorecard-difficulty');
  const scorecardSessionId = document.getElementById('scorecard-session-id');
  const scorePercentageVal = document.getElementById('score-percentage-val');
  const scoreCircleFill = document.getElementById('score-circle-fill');
  const hiringRecommendationBadge = document.getElementById('hiring-recommendation-badge');
  const statTotalQ = document.getElementById('stat-total-q');
  const statCorrectCount = document.getElementById('stat-correct-count');
  const statPartialCount = document.getElementById('stat-partial-count');
  const statIncorrectCount = document.getElementById('stat-incorrect-count');
  const scorecardExecutiveSummary = document.getElementById('scorecard-executive-summary');
  const scorecardTopStrengths = document.getElementById('scorecard-top-strengths');
  const scorecardAreasGrowth = document.getElementById('scorecard-areas-growth');
  const skillBreakdownContainer = document.getElementById('skill-breakdown-container');
  const questionsReviewAccordion = document.getElementById('questions-review-accordion');
  const btnPrintScorecard = document.getElementById('btn-print-scorecard');
  const btnRestartInterview = document.getElementById('btn-restart-interview');


  // ================= UTILITIES & NAVIGATION =================
  function showStage(stageId) {
    [stageSetup, stageInterview, stageScorecard].forEach(el => el.classList.remove('active'));
    document.getElementById(stageId).classList.add('active');

    if (stageId === 'stage-interview') {
      btnResetApp.style.display = 'inline-flex';
    } else if (stageId === 'stage-setup') {
      btnResetApp.style.display = 'none';
      stopTimer();
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (window.lucide) window.lucide.createIcons();
  }

  // Timer
  function startTimer() {
    state.secondsElapsed = 0;
    clearInterval(state.timerInterval);
    state.timerInterval = setInterval(() => {
      state.secondsElapsed++;
      const mins = Math.floor(state.secondsElapsed / 60).toString().padStart(2, '0');
      const secs = (state.secondsElapsed % 60).toString().padStart(2, '0');
      interviewTimer.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  function stopTimer() {
    clearInterval(state.timerInterval);
  }

  // Check Server Health
  async function checkServerHealth() {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      if (!data.has_server_gemini_key) {
        console.warn('Note: GEMINI_API_KEY is not configured in .env');
      }
    } catch (e) {
      console.warn('Server check failed', e);
    }
  }
  checkServerHealth();


  // ================= STAGE 1: RESUME UPLOAD =================
  dropzone.addEventListener('click', () => {
    resumeFileInput.click();
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  resumeFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  });

  btnReupload.addEventListener('click', (e) => {
    e.stopPropagation();
    resumeFileInput.value = '';
    state.resumeId = null;
    dropzoneContent.style.display = 'block';
    uploadSuccess.style.display = 'none';
    sectionsPreview.style.display = 'none';
    btnStartInterview.disabled = true;
    ctaHint.textContent = 'Please upload a resume first to unlock the interview.';
    ctaHint.style.color = 'var(--text-muted)';
  });

  async function handleFileUpload(file) {
    const validExts = ['.pdf', '.txt'];
    const hasValidExt = validExts.some(ext => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
      alert('Please upload a PDF (.pdf) or Text (.txt) resume file.');
      return;
    }

    dropzoneContent.style.display = 'none';
    uploadSpinner.style.display = 'block';
    uploadSuccess.style.display = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload-resume', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      uploadSpinner.style.display = 'none';

      if (!response.ok || !data.success) {
        throw new Error(data.detail || 'Resume parsing failed');
      }

      // Success
      state.resumeId = data.resume_id;
      uploadedFilename.textContent = data.filename;
      uploadedMeta.textContent = '✓ Resume verified & ready for interview';
      uploadSuccess.style.display = 'block';

      // Render Detected Sections
      detectedTags.innerHTML = '';
      data.detected_sections.forEach(sec => {
        const span = document.createElement('span');
        span.className = 'section-tag';
        span.textContent = sec;
        detectedTags.appendChild(span);
      });
      sectionsPreview.style.display = 'block';

      // Enable Start Interview
      btnStartInterview.disabled = false;
      ctaHint.textContent = '✓ Resume processed & indexed. Ready to start your interview!';
      ctaHint.style.color = 'var(--color-success)';

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      uploadSpinner.style.display = 'none';
      dropzoneContent.style.display = 'block';
      alert('Error uploading resume: ' + err.message);
    }
  }

  // Quick Role Pills
  rolePills.forEach(pill => {
    pill.addEventListener('click', () => {
      targetRoleInput.value = pill.dataset.role;
    });
  });

  // Start Interview Submission
  interviewConfigForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.resumeId) {
      alert('Please upload a resume first.');
      return;
    }

    const targetRole = targetRoleInput.value.trim();
    const difficulty = document.querySelector('input[name="difficulty"]:checked').value;
    const totalQuestions = parseInt(document.querySelector('input[name="num-questions"]:checked').value, 10);

    btnStartInterview.disabled = true;
    btnStartInterview.querySelector('.btn-text').textContent = 'Analyzing Resume & Crafting Questions...';

    try {
      const payload = {
        resume_id: state.resumeId,
        target_role: targetRole,
        difficulty: difficulty,
        total_questions: totalQuestions
      };

      const res = await fetch('/api/start-interview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to start interview');
      }

      state.sessionId = data.session_id;
      state.totalQuestions = data.total_questions;
      state.currentQuestionIndex = 1;

      // Load First Question
      await loadQuestion(1);
      showStage('stage-interview');
      startTimer();
    } catch (err) {
      alert('Error initializing interview: ' + err.message);
    } finally {
      btnStartInterview.disabled = false;
      btnStartInterview.querySelector('.btn-text').textContent = 'Generate AI Interview Session';
    }
  });


  // ================= STAGE 2: LIVE INTERVIEW ARENA =================
  async function loadQuestion(qIndex) {
    state.currentQuestionIndex = qIndex;
    currentQNum.textContent = qIndex;
    totalQNum.textContent = state.totalQuestions;

    // Progress Bar
    const progressPercent = Math.round((qIndex / state.totalQuestions) * 100);
    interviewProgressFill.style.width = `${progressPercent}%`;

    // Clear Previous inputs & Drawer
    answerInput.value = '';
    updateWordCount();
    evaluationDrawer.style.display = 'none';
    btnSubmitAnswer.disabled = false;
    btnSkipQuestion.disabled = false;
    submitBtnText.textContent = 'Submit & Evaluate Answer';

    try {
      const res = await fetch(`/api/session/${state.sessionId}/question/${qIndex}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not load question');

      state.activeQuestion = data;
      questionCategory.textContent = data.category || 'Technical';
      activeQuestionText.textContent = data.question_text;
      activeResumeContext.textContent = data.resume_context || 'Relevant to your overall profile and target role.';

      // If already answered, populate
      if (data.is_answered && data.answer_data) {
        answerInput.value = data.answer_data.candidate_answer;
        updateWordCount();
        displayEvaluationDrawer(data.answer_data, qIndex < state.totalQuestions);
      }

      answerInput.focus();
    } catch (err) {
      alert('Failed to load question: ' + err.message);
    }
  }

  function updateWordCount() {
    const text = answerInput.value.trim();
    const count = text ? text.split(/\s+/).length : 0;
    wordCount.textContent = `${count} word${count === 1 ? '' : 's'}`;
  }

  answerInput.addEventListener('input', updateWordCount);

  // Voice Input (Web Speech API)
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = true;
    state.recognition.interimResults = true;

    state.recognition.onstart = () => {
      state.isRecording = true;
      btnVoiceInput.classList.add('recording');
      micStatusText.textContent = 'Listening...';
    };

    state.recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript + ' ';
        }
      }
      if (finalTranscript) {
        answerInput.value = (answerInput.value + ' ' + finalTranscript).trim();
        updateWordCount();
      }
    };

    state.recognition.onerror = (e) => {
      console.warn('Speech recognition error:', e.error);
      stopRecording();
    };

    state.recognition.onend = () => {
      stopRecording();
    };

    function stopRecording() {
      state.isRecording = false;
      btnVoiceInput.classList.remove('recording');
      micStatusText.textContent = 'Voice Input';
    }

    btnVoiceInput.addEventListener('click', () => {
      if (state.isRecording) {
        state.recognition.stop();
      } else {
        state.recognition.start();
      }
    });
  } else {
    btnVoiceInput.style.display = 'none';
  }

  // Answer Submission
  btnSubmitAnswer.addEventListener('click', async () => {
    const answer = answerInput.value.trim();
    if (!answer) {
      alert('Please type or speak your answer before submitting.');
      return;
    }
    await processAnswerSubmission(answer);
  });

  btnSkipQuestion.addEventListener('click', async () => {
    if (confirm('Are you sure you want to skip this question? It will be marked as unanswered.')) {
      await processAnswerSubmission('I am choosing to skip this question.');
    }
  });

  async function processAnswerSubmission(candidateAnswer) {
    btnSubmitAnswer.disabled = true;
    btnSkipQuestion.disabled = true;
    submitBtnText.textContent = 'Verifying with RAG & Grading...';

    try {
      const payload = {
        question_id: state.activeQuestion.question_id,
        candidate_answer: candidateAnswer
      };

      const res = await fetch(`/api/session/${state.sessionId}/submit-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Submission failed');
      }

      displayEvaluationDrawer(data.evaluation, data.has_next);
    } catch (err) {
      alert('Error submitting answer: ' + err.message);
      btnSubmitAnswer.disabled = false;
      btnSkipQuestion.disabled = false;
      submitBtnText.textContent = 'Submit & Evaluate Answer';
    }
  }

  function displayEvaluationDrawer(evaluation, hasNext) {
    const status = evaluation.correctness_status || (evaluation.score >= 8.0 ? 'Correct' : evaluation.score >= 5.0 ? 'Partially Correct' : 'Incorrect');

    evalStatusBadge.textContent = status;
    evalStatusBadge.className = 'correctness-pill';
    if (status === 'Correct') {
      evalStatusBadge.classList.add('correct');
    } else if (status === 'Partially Correct') {
      evalStatusBadge.classList.add('partial');
    } else {
      evalStatusBadge.classList.add('incorrect');
    }

    evalScoreNum.textContent = `${evaluation.score} / 10`;
    evalFeedback.textContent = evaluation.feedback || 'Evaluated successfully.';

    // Strengths
    evalStrengthsList.innerHTML = '';
    (evaluation.strengths || []).forEach(s => {
      const li = document.createElement('li');
      li.textContent = s;
      evalStrengthsList.appendChild(li);
    });

    // Improvements
    evalImprovementsList.innerHTML = '';
    (evaluation.improvements || []).forEach(i => {
      const li = document.createElement('li');
      li.textContent = i;
      evalImprovementsList.appendChild(li);
    });

    // Ideal Answer
    evalIdealAnswer.textContent = evaluation.ideal_answer_summary || 'A comprehensive response covers core architecture and concrete trade-offs.';

    if (hasNext) {
      nextQText.textContent = `Proceed to Question ${state.currentQuestionIndex + 1}`;
    } else {
      nextQText.textContent = 'View Final Scorecard';
    }

    evaluationDrawer.style.display = 'block';
    evaluationDrawer.scrollIntoView({ behavior: 'smooth' });
    if (window.lucide) window.lucide.createIcons();
  }

  btnCloseEval.addEventListener('click', () => {
    evaluationDrawer.style.display = 'none';
  });

  btnNextQuestion.addEventListener('click', async () => {
    if (state.currentQuestionIndex < state.totalQuestions) {
      await loadQuestion(state.currentQuestionIndex + 1);
    } else {
      await loadScorecard();
    }
  });


  // ================= STAGE 3: FINAL SCORECARD =================
  async function loadScorecard() {
    stopTimer();
    showStage('stage-scorecard');

    scorePercentageVal.textContent = '...';
    hiringRecommendationBadge.textContent = 'Calculating Final Scorecard...';

    try {
      const res = await fetch(`/api/session/${state.sessionId}/scorecard`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not compile scorecard');

      renderScorecard(data);
    } catch (err) {
      alert('Error generating scorecard: ' + err.message);
    }
  }

  function renderScorecard(data) {
    scorecardRole.textContent = data.target_role;
    scorecardDifficulty.textContent = data.difficulty;
    scorecardSessionId.textContent = data.session_id.substring(0, 8);

    // Percentage & Animated Donut
    const percentage = data.overall_score;
    scorePercentageVal.textContent = `${percentage}%`;

    // SVG dashoffset: full circle is ~314.16
    const circumference = 314.16;
    const offset = circumference - (percentage / 100) * circumference;
    scoreCircleFill.style.strokeDashoffset = offset;

    // Recommendation
    hiringRecommendationBadge.textContent = data.hiring_recommendation;

    // Stat counts (Sahi vs Galat)
    statTotalQ.textContent = data.total_questions;
    statCorrectCount.textContent = data.correct_count;
    statPartialCount.textContent = data.partially_correct_count;
    statIncorrectCount.textContent = data.incorrect_count;

    // Executive summary & Lists
    scorecardExecutiveSummary.textContent = data.summary_feedback;

    scorecardTopStrengths.innerHTML = '';
    (data.top_strengths || []).forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      scorecardTopStrengths.appendChild(li);
    });

    scorecardAreasGrowth.innerHTML = '';
    (data.areas_for_growth || []).forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      scorecardAreasGrowth.appendChild(li);
    });

    // Skill Breakdown Meters
    skillBreakdownContainer.innerHTML = '';
    const breakdown = data.skill_breakdown || {};
    Object.entries(breakdown).forEach(([category, score]) => {
      const div = document.createElement('div');
      div.className = 'skill-meter-item';
      div.innerHTML = `
        <div class="meter-labels">
          <span>${category}</span>
          <strong>${score}%</strong>
        </div>
        <div class="meter-track">
          <div class="meter-bar" style="width: ${score}%;"></div>
        </div>
      `;
      skillBreakdownContainer.appendChild(div);
    });

    // Detailed Question Breakdown Accordion
    questionsReviewAccordion.innerHTML = '';
    (data.questions_review || []).forEach((q, idx) => {
      const isCorrect = q.correctness_status === 'Correct';
      const isPartial = q.correctness_status === 'Partially Correct';
      const statusClass = isCorrect ? 'correct' : isPartial ? 'partial' : 'incorrect';

      const itemDiv = document.createElement('div');
      itemDiv.className = `accordion-item ${idx === 0 ? 'open' : ''}`;
      itemDiv.innerHTML = `
        <div class="accordion-header">
          <div class="accordion-header-left">
            <span class="q-index-pill">Q${q.q_index}</span>
            <span class="q-title-text">${q.question}</span>
          </div>
          <div class="accordion-header-right">
            <span class="correctness-pill ${statusClass}">${q.correctness_status}</span>
            <span class="q-score-tag">${q.score}/10</span>
            <i data-lucide="chevron-down" class="chevron-icon"></i>
          </div>
        </div>
        <div class="accordion-body">
          <div class="review-detail-box">
            <span class="detail-label">Tested Resume Claim / Concept:</span>
            <p class="detail-content">${q.resume_context || 'General Role Competency'}</p>
          </div>
          <div class="review-detail-box">
            <span class="detail-label">Your Submitted Answer:</span>
            <p class="detail-content">${q.candidate_answer}</p>
          </div>
          <div class="review-detail-box">
            <span class="detail-label">Interviewer Assessment:</span>
            <p class="detail-content">${q.feedback}</p>
          </div>
          ${q.ideal_answer_summary ? `
          <div class="review-detail-box">
            <span class="detail-label">Ideal Technical Answer:</span>
            <p class="detail-content">${q.ideal_answer_summary}</p>
          </div>` : ''}
        </div>
      `;

      // Accordion toggle
      const header = itemDiv.querySelector('.accordion-header');
      header.addEventListener('click', () => {
        itemDiv.classList.toggle('open');
      });

      questionsReviewAccordion.appendChild(itemDiv);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  btnPrintScorecard.addEventListener('click', () => {
    window.print();
  });

  btnRestartInterview.addEventListener('click', resetAll);
  btnResetApp.addEventListener('click', resetAll);

  function resetAll() {
    if (confirm('Do you want to start a new interview session?')) {
      state.sessionId = null;
      state.currentQuestionIndex = 1;
      stopTimer();
      showStage('stage-setup');
    }
  }


  // ================= DYNAMIC FUTURISTIC AI CURSOR =================
  function initDynamicCursor() {
    const dot = document.getElementById('cursor-dot');
    const ring = document.getElementById('cursor-ring');
    if (!dot || !ring) return;

    let mouseX = -200, mouseY = -200;
    let ringX = -200, ringY = -200;
    let isVisible = false;
    let lastParticleTime = 0;
    let isTouchDevice = false;

    function activateCursor() {
      if (!isVisible && !isTouchDevice) {
        isVisible = true;
        document.documentElement.classList.add('custom-cursor-active');
        dot.classList.remove('cursor-hidden');
        ring.classList.remove('cursor-hidden');
      }
    }

    // Touch device detection: don't show custom cursor if user is tapping with fingers
    window.addEventListener('touchstart', () => {
      isTouchDevice = true;
      isVisible = false;
      document.documentElement.classList.remove('custom-cursor-active');
      dot.classList.add('cursor-hidden');
      ring.classList.add('cursor-hidden');
    }, { passive: true });

    // Tracking for pointer dot
    window.addEventListener('mousemove', (e) => {
      // If previously switched to touch, moving mouse re-enables mouse mode
      isTouchDevice = false;
      activateCursor();

      mouseX = e.clientX;
      mouseY = e.clientY;

      dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0) translate(-50%, -50%) scale(var(--cursor-scale, 1))`;

      // Subtle particle trail when moving swiftly
      const now = Date.now();
      if (now - lastParticleTime > 40) {
        createCursorParticle(mouseX, mouseY);
        lastParticleTime = now;
      }
    });

    // Smooth Lerp loop for trailing outer ring
    function loop() {
      // Buttery smooth physics follow
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;

      ring.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%) scale(var(--ring-scale, 1))`;
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);

    // Glowing Particle Effect
    function createCursorParticle(x, y) {
      if (isTouchDevice || !isVisible) return;
      const p = document.createElement('div');
      p.className = 'cursor-particle';
      const offsetX = (Math.random() - 0.5) * 14;
      const offsetY = (Math.random() - 0.5) * 14;
      p.style.left = `${x + offsetX}px`;
      p.style.top = `${y + offsetY}px`;
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 550);
    }

    // Hover detection on interactive elements
    const interactiveQuery = 'button, a, input, textarea, select, .role-card, .role-pill, .upload-dropzone, .btn, .btn-primary, .btn-ghost, .btn-secondary, .accordion-header, .faq-question, [role="button"], label, [tabindex], .badge, .status-pill, .theme-toggle-btn';

    document.addEventListener('mouseover', (e) => {
      const target = e.target.closest(interactiveQuery);
      if (target) {
        const isInput = target.matches('input, textarea, [contenteditable="true"]');
        if (isInput) {
          ring.classList.add('cursor-text');
          dot.classList.add('cursor-text');
        } else {
          ring.classList.add('cursor-hover');
          dot.classList.add('cursor-hover');
        }
      }
    });

    document.addEventListener('mouseout', (e) => {
      const target = e.target.closest(interactiveQuery);
      if (target) {
        ring.classList.remove('cursor-hover', 'cursor-text');
        dot.classList.remove('cursor-hover', 'cursor-text');
      }
    });

    // Click pulse reactions
    window.addEventListener('mousedown', () => {
      ring.classList.add('cursor-click');
      dot.classList.add('cursor-click');
    });

    window.addEventListener('mouseup', () => {
      ring.classList.remove('cursor-click');
      dot.classList.remove('cursor-click');
    });

    // Window focus / leave detection
    document.addEventListener('mouseleave', () => {
      isVisible = false;
      dot.classList.add('cursor-hidden');
      ring.classList.add('cursor-hidden');
    });

    document.addEventListener('mouseenter', () => {
      if (!isTouchDevice) {
        isVisible = true;
        dot.classList.remove('cursor-hidden');
        ring.classList.remove('cursor-hidden');
      }
    });
  }

  // Initialize dynamic cursor
  initDynamicCursor();

});

const UI = {
    modeScreen: document.getElementById('mode-screen'),
    loading: document.getElementById('loading'),
    gameArea: document.getElementById('game-area'),
    questionRow: document.getElementById('question-row'),
    questionText: document.getElementById('question-text'),
    ballIcon: document.getElementById('ball-icon'),
    optionsContainer: document.getElementById('options-container'),
    feedback: document.getElementById('feedback'),
    nextBtn: document.getElementById('next-btn'),
    streakCounter: document.getElementById('streak-counter'),
    winScreen: document.getElementById('win-screen'),
    resetBtn: document.getElementById('reset-game-btn'),
    keepPlayingBtn: document.getElementById('keep-playing-btn'),
    loseScreen: document.getElementById('lose-screen'),
    loseMessage: document.getElementById('lose-message'),
    loseResetBtn: document.getElementById('lose-reset-btn'),
    shareWinBtn: document.getElementById('share-win-btn'),
    shareLoseBtn: document.getElementById('share-lose-btn'),
    batterIcon: document.getElementById('batter-icon'),
    runnerIcon: document.getElementById('runner-icon'),
    livesContainer: document.getElementById('lives-container')
};

let typingInterval = null;
let typingTimeout = null;

let players = [];
let currentOptions = [];
let currentStat = null;
let currentAnswer = null;
let currentDirectionLabel = null;
let streak = 0;
let lives = 3;
let winScreenShown = false;
let selectedMode = null;

const STAT_CONFIG = {
    hitter: ['Home Runs', 'Hits', 'Batting Average'],
    pitcher: ['ERA', 'Strikeouts', 'Wins']
};

// Base positions in SVG coordinates (translate values for the runner icon)
const BASE_POSITIONS = {
    home: { x: 150, y: 195 },
    first: { x: 220, y: 125 },
    second: { x: 150, y: 55 },
    third: { x: 80, y: 125 }
};

function selectMode(mode) {
    selectedMode = mode;

    // Animate mode screen out
    UI.modeScreen.classList.add('mode-exit');
    setTimeout(() => {
        UI.modeScreen.classList.add('hidden');
        UI.modeScreen.classList.remove('mode-exit');
        init();
    }, 400);
}

// Expose selectMode globally for onclick handlers
window.selectMode = selectMode;

async function init() {
    try {
        UI.loading.classList.remove('hidden');

        // Choose the correct JSON file based on selected mode
        let jsonFile;
        if (selectedMode === 'alltime') jsonFile = 'players_alltime.json';
        else if (selectedMode === 'current') jsonFile = 'players_current.json';
        else jsonFile = 'players_modern.json';
        const res = await fetch(jsonFile);
        players = await res.json();

        if (!players || players.length === 0) {
            throw new Error('No players found');
        }

        UI.loading.classList.add('hidden');
        UI.gameArea.style.display = 'block';
        updateRunner();
        nextRound();
    } catch (e) {
        console.error(e);
        UI.loading.innerText = 'Failed to load player data.';
    }
}

function nextRound() {
    // Pick random type
    const types = ['hitter', 'pitcher'];
    const selectedType = types[Math.floor(Math.random() * types.length)];

    // Pick random stat from that type
    const availableStats = STAT_CONFIG[selectedType];
    currentStat = availableStats[Math.floor(Math.random() * availableStats.length)];

    // Generate options and determine winner
    currentOptions = generateOptions(selectedType, currentStat);

    // The correct answer is the player with the "best" stat
    const bestPlayer = determineWinner(currentOptions, currentStat);
    currentAnswer = bestPlayer.name;

    // Build question
    const countingStats = ['Home Runs', 'Hits', 'Strikeouts', 'Wins'];
    const rateStats = ['Batting Average', 'ERA'];
    const isLowestBetter = (currentStat === 'ERA');

    if (countingStats.includes(currentStat)) {
        currentDirectionLabel = isLowestBetter ? 'fewest' : 'most';
    } else {
        currentDirectionLabel = isLowestBetter ? 'lowest' : 'highest';
    }

    const questionText = `Which of these players has the ${currentDirectionLabel} career ${currentStat}?`;

    // Reset UI
    UI.optionsContainer.innerHTML = '';
    UI.feedback.className = 'feedback hidden';
    UI.nextBtn.classList.add('hidden');

    // Play typewriter animation
    playTypewriterAnimation(questionText);

    // Create buttons
    currentOptions.forEach(player => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.dataset.name = player.name;
        btn.innerText = player.name;
        btn.onclick = () => checkAnswer(player.name, btn);
        UI.optionsContainer.appendChild(btn);
    });
}

function generateOptions(type, statName, depth = 0) {
    // Pick a seed player
    const typePlayers = players.filter(p => p.type === type);
    const seed = typePlayers[Math.floor(Math.random() * typePlayers.length)];

    // Find all other peers of same type
    let peers = typePlayers.filter(p => p.name !== seed.name);

    // Sort by WAR similarity
    peers.sort((a, b) => Math.abs(a.war - seed.war) - Math.abs(b.war - seed.war));

    // Take 10 closest
    let pool = peers.slice(0, 10);

    // Randomly pick 3 from the pool
    let selectedPeers = [];
    while (selectedPeers.length < 3 && pool.length > 0) {
        const idx = Math.floor(Math.random() * pool.length);
        selectedPeers.push(pool.splice(idx, 1)[0]);
    }

    let options = [seed, ...selectedPeers];

    // Ensure there is only one winner. 
    // depth < 5 prevents infinite recursion in case of bad data.
    if (hasTie(options, statName) && depth < 5) {
        return generateOptions(type, statName, depth + 1);
    }

    return options.sort(() => Math.random() - 0.5);
}

function determineWinner(options, statName) {
    let winner = options[0];
    const isLowestBetter = (statName === 'ERA');

    options.forEach(p => {
        const val = p.stats[statName];
        const winVal = winner.stats[statName];

        // Use formatted values to ensure the winner matches what players see
        const fmtVal = parseFloat(formatStatValue(statName, val).replace(/[^0-9.]/g, ''));
        const fmtWinVal = parseFloat(formatStatValue(statName, winVal).replace(/[^0-9.]/g, ''));

        if (isLowestBetter) {
            if (fmtVal < fmtWinVal) winner = p;
        } else {
            if (fmtVal > fmtWinVal) winner = p;
        }
    });

    return winner;
}

function hasTie(options, statName) {
    // Compare formatted values because that's what the user sees
    const values = options.map(p => {
        const fmt = formatStatValue(statName, p.stats[statName]);
        // Remove leading dot or other symbols for numerical comparison if needed, 
        // but simple string comparison works for ties if formatting is identical.
        return fmt;
    });

    const isLowestBetter = (statName === 'ERA');

    // Find "best" formatted value
    let bestValue = values[0];
    values.forEach(v => {
        const numV = parseFloat(v.startsWith('.') ? '0' + v : v);
        const numBest = parseFloat(bestValue.startsWith('.') ? '0' + bestValue : bestValue);

        if (isLowestBetter) {
            if (numV < numBest) bestValue = v;
        } else {
            if (numV > numBest) bestValue = v;
        }
    });

    let count = 0;
    values.forEach(v => {
        if (v === bestValue) count++;
    });
    return count > 1;
}

function formatStatValue(statName, value) {
    if (statName === 'Batting Average') {
        let text = parseFloat(value).toFixed(3);
        if (text.startsWith('0.')) text = text.substring(1);
        return text;
    }
    if (statName === 'ERA') {
        return parseFloat(value).toFixed(2);
    }
    return String(value);
}

function checkAnswer(selectedName, selectedBtn) {
    const isCorrect = selectedName === currentAnswer;

    // Reveal stats for all buttons
    const buttons = UI.optionsContainer.querySelectorAll('.option-btn');
    buttons.forEach((b) => {
        b.disabled = true;
        const player = currentOptions.find(p => p.name === b.dataset.name);
        if (player) {
            const formattedVal = formatStatValue(currentStat, player.stats[currentStat]);
            b.innerHTML = `${player.name} <span class="stat-reveal">(${formattedVal} ${currentStat})</span>`;

            if (player.name === currentAnswer) {
                b.classList.add('correct');
            }
        }
    });

    if (!isCorrect) {
        selectedBtn.classList.add('incorrect');
    }

    if (isCorrect) {
        streak++;
        UI.feedback.className = 'feedback success';
        UI.streakCounter.parentElement.style.transform = 'scale(1.1)';
        setTimeout(() => UI.streakCounter.parentElement.style.transform = 'scale(1)', 200);
        UI.feedback.innerHTML = `Correct! <strong>${currentAnswer}</strong> has the ${currentDirectionLabel}.`;
    } else {
        lives--;
        updateLivesUI();

        if (lives === 0) {
            UI.loseMessage.innerHTML = `The correct answer was <strong>${currentAnswer}</strong>. Your streak of <strong>${streak}</strong> has ended.`;
            setTimeout(() => {
                UI.loseScreen.classList.remove('hidden');
            }, 500);
        } else {
            UI.feedback.className = 'feedback error';
            UI.feedback.innerHTML = `Incorrect! That was <strong>${currentAnswer}</strong>.`;

            // Shake the lives container
            UI.livesContainer.classList.remove('shake');
            void UI.livesContainer.offsetWidth; // force reflow to restart animation
            UI.livesContainer.classList.add('shake');
        }
    }

    UI.streakCounter.innerText = streak;
    updateRunner();

    if (streak === 4 && !winScreenShown) {
        winScreenShown = true;
        setTimeout(() => {
            UI.winScreen.classList.remove('hidden');
        }, 500);
    } else {
        UI.nextBtn.classList.remove('hidden');
        UI.nextBtn.focus();
    }
}

function updateRunner() {
    const position = streak % 4;

    if (position === 0) {
        // Show batter at home, hide runner
        UI.batterIcon.style.display = '';
        UI.runnerIcon.style.display = 'none';
    } else {
        // Hide batter, show runner at the appropriate base
        UI.batterIcon.style.display = 'none';
        UI.runnerIcon.style.display = '';

        let pos;
        if (position === 1) pos = BASE_POSITIONS.first;
        else if (position === 2) pos = BASE_POSITIONS.second;
        else pos = BASE_POSITIONS.third;

        UI.runnerIcon.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
    }
}

function updateLivesUI() {
    const hearts = UI.livesContainer.querySelectorAll('.heart');
    hearts.forEach((heart, index) => {
        if (index >= lives) {
            heart.classList.add('lost');
        } else {
            heart.classList.remove('lost');
        }
    });
}

function resetGame() {
    streak = 0;
    lives = 3;
    winScreenShown = false;
    updateLivesUI();
    UI.streakCounter.innerText = streak;
    UI.winScreen.classList.add('hidden');
    UI.loseScreen.classList.add('hidden');
    UI.gameArea.style.display = 'none';

    // Show mode selection again
    UI.modeScreen.classList.remove('hidden');
}

function keepPlaying() {
    UI.winScreen.classList.add('hidden');
    UI.nextBtn.classList.remove('hidden');
    UI.nextBtn.focus();
}

function playTypewriterAnimation(text) {
    // Clear any pending animation
    if (typingInterval) clearInterval(typingInterval);
    if (typingTimeout) clearTimeout(typingTimeout);

    UI.questionText.textContent = '';
    UI.ballIcon.classList.remove('ball-hidden');
    UI.ballIcon.classList.add('ball-visible');
    UI.questionRow.classList.add('animating');

    let charIndex = 0;
    const totalChars = text.length;
    const charDelay = 25; // ms per character

    typingInterval = setInterval(() => {
        if (charIndex < totalChars) {
            UI.questionText.textContent += text[charIndex];
            charIndex++;
        } else {
            clearInterval(typingInterval);
            typingInterval = null;

            // Just keep the ball at the end for 300ms then hide
            typingTimeout = setTimeout(() => {
                UI.ballIcon.classList.remove('ball-visible');
                UI.ballIcon.classList.add('ball-hidden');
                UI.questionRow.classList.remove('animating');
            }, 300);
        }
    }, charDelay);
}

UI.nextBtn.addEventListener('click', nextRound);
UI.resetBtn.addEventListener('click', resetGame);
UI.loseResetBtn.addEventListener('click', resetGame);
UI.keepPlayingBtn.addEventListener('click', keepPlaying);
UI.shareWinBtn.addEventListener('click', () => shareResult(true));
UI.shareLoseBtn.addEventListener('click', () => shareResult(false));

function shareResult(won) {
    const modeLabels = { alltime: 'All-Time', modern: 'Since 2000', current: 'Current Players' };
    const modeLabel = modeLabels[selectedMode] || selectedMode;
    const mistakes = 3 - lives;
    const text = (won && streak === 4)
        ? `⚾ I just beat Baseball Stat Quiz (${modeLabel} mode) with only ${mistakes} mistake${mistakes === 1 ? '' : 's'}! Can you do it? baseballstatquiz.com`
        : `⚾ I reached a streak of ${streak} on Baseball Stat Quiz (${modeLabel} mode). Can you beat me? baseballstatquiz.com`;

    if (navigator.share) {
        navigator.share({ text }).catch(() => {});
    } else {
        navigator.clipboard.writeText(text).then(() => {
            const btn = won ? UI.shareWinBtn : UI.shareLoseBtn;
            const original = btn.textContent;
            btn.textContent = '✅ Copied!';
            setTimeout(() => btn.textContent = original, 2000);
        });
    }
}

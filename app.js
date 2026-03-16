const UI = {
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
    batterIcon: document.getElementById('batter-icon'),
    runnerIcon: document.getElementById('runner-icon'),
    livesContainer: document.getElementById('lives-container')
};

let typingInterval = null;
let typingTimeout = null;

let players = [];
let currentPlayer = null;
let currentStat = null;
let currentAnswer = null;
let streak = 0;
let lives = 3;
let winScreenShown = false;

// Base positions in SVG coordinates (translate values for the runner icon)
const BASE_POSITIONS = {
    home:   { x: 150, y: 195 },
    first:  { x: 220, y: 125 },
    second: { x: 150, y: 55 },
    third:  { x: 80,  y: 125 }
};

async function init() {
    try {
        const res = await fetch('players.json');
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
    // Pick random player
    currentPlayer = players[Math.floor(Math.random() * players.length)];
    
    // Pick random stat
    const stats = Object.keys(currentPlayer.stats);
    currentStat = stats[Math.floor(Math.random() * stats.length)];
    currentAnswer = currentPlayer.name;

    const statValue = currentPlayer.stats[currentStat];
    const formattedValue = formatStatValue(currentStat, statValue);
    const typeLabel = currentPlayer.type === 'hitter' ? 'hitters' : 'pitchers';

    // Build question as plain text for typewriter
    const questionPlain = `Which of these ${typeLabel} had a career ${currentStat} of ${formattedValue}?`;
    
    // Reset UI
    UI.optionsContainer.innerHTML = '';
    UI.feedback.className = 'feedback hidden';
    UI.nextBtn.classList.add('hidden');

    // Play typewriter animation
    playTypewriterAnimation(questionPlain);

    // Generate player-name options
    const options = generateOptions(currentPlayer, currentStat);
    
    options.forEach(playerName => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.innerText = playerName;
        btn.onclick = () => checkAnswer(playerName, btn);
        UI.optionsContainer.appendChild(btn);
    });
}

function generateOptions(playerObj, statName) {
    const correctName = playerObj.name;
    const correctValue = formatStatValue(statName, playerObj.stats[statName]);
    
    let optionNames = new Set();
    optionNames.add(correctName);
    let options = [correctName];
    
    let peers = players.filter(p => p.type === playerObj.type && p.name !== playerObj.name);
    peers.sort((a, b) => Math.abs(a.war - playerObj.war) - Math.abs(b.war - playerObj.war));
    
    let peerIndex = 0;
    while (options.length < 4 && peerIndex < peers.length) {
        const peer = peers[peerIndex];
        peerIndex++;
        if (optionNames.has(peer.name)) continue;
        const peerValue = formatStatValue(statName, peer.stats[statName]);
        if (peerValue === correctValue) continue;
        optionNames.add(peer.name);
        options.push(peer.name);
    }
    
    // Fallback
    peerIndex = 0;
    while (options.length < 4 && peerIndex < peers.length) {
        const peer = peers[peerIndex];
        peerIndex++;
        if (!optionNames.has(peer.name)) {
            optionNames.add(peer.name);
            options.push(peer.name);
        }
    }
    
    return options.sort(() => Math.random() - 0.5);
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
    
    const buttons = UI.optionsContainer.querySelectorAll('.option-btn');
    buttons.forEach(b => {
        b.disabled = true;
        if (b.innerText === currentAnswer) {
            b.classList.add('correct');
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
        UI.feedback.innerHTML = `Correct! It was <strong>${currentAnswer}</strong>.`;
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
            UI.livesContainer.style.transform = 'translateX(-5px)';
            setTimeout(() => UI.livesContainer.style.transform = 'translateX(5px)', 50);
            setTimeout(() => UI.livesContainer.style.transform = 'translateX(-5px)', 100);
            setTimeout(() => UI.livesContainer.style.transform = 'translateX(5px)', 150);
            setTimeout(() => UI.livesContainer.style.transform = 'translateX(0)', 200);
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
        
        UI.runnerIcon.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
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
    updateRunner();
    nextRound();
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

// Initialize the game
init();

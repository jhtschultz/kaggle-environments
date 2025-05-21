// --- Constants ---
const DEFAULT_NUM_ROWS = 6;
const DEFAULT_NUM_COLS = 7;
const PLAYER_X_CLASS = 'player-x';
const PLAYER_O_CLASS = 'player-o';

// --- Global state for renderer elements (to avoid recreating them) ---
let boardElement = null;
let statusTextElement = null;
let winnerTextElement = null;
let messageBoxElement = null;
let rendererContainer = null;
let titleElement = null;

// --- Helper to show messages ---
function showMessage(message, type = 'info', duration = 3000) {
    if (!messageBoxElement && document.body) { // Create if doesn't exist and body is available
        messageBoxElement = document.createElement('div');
        messageBoxElement.id = 'messageBox'; // Assign an ID for potential future reference
        // Apply styling for the message box (should match CSS from the HTML version)
        messageBoxElement.style.position = 'fixed';
        messageBoxElement.style.top = '10px';
        messageBoxElement.style.left = '50%';
        messageBoxElement.style.transform = 'translateX(-50%)';
        messageBoxElement.style.padding = '0.75rem 1rem';
        messageBoxElement.style.borderRadius = '0.375rem';
        messageBoxElement.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
        messageBoxElement.style.zIndex = '1000';
        messageBoxElement.style.opacity = '0';
        messageBoxElement.style.transition = 'opacity 0.3s ease-in-out, background-color 0.3s';
        messageBoxElement.style.fontSize = '0.875rem';
        messageBoxElement.style.fontFamily = "'Inter', sans-serif"; // Match body font
        document.body.appendChild(messageBoxElement);
    }

    if (messageBoxElement) {
        messageBoxElement.textContent = message;
        // Basic styling reset and application
        messageBoxElement.style.backgroundColor = type === 'error' ? '#ef4444' : '#10b981'; // red-500 or green-500
        messageBoxElement.style.color = 'white';
        messageBoxElement.style.opacity = '1'; // Show
        setTimeout(() => {
            if (messageBoxElement) messageBoxElement.style.opacity = '0'; // Hide
        }, duration);
    } else {
        // Fallback if messageBoxElement couldn't be created (e.g., document.body not ready)
        console.log(`ConnectFourRenderer (${type}): ${message}`);
    }
}

// --- DOM Manipulation ---
function ensureRendererElements(parentElement, rows, cols) {
    if (!parentElement) {
        console.error("ConnectFourRenderer: Parent element is null. Cannot create renderer elements.");
        return false;
    }

    if (!rendererContainer) {
        parentElement.innerHTML = ''; // Clear the parent element only once

        rendererContainer = document.createElement('div');
        // Styles for rendererContainer (mimicking Tailwind classes)
        rendererContainer.style.display = 'flex';
        rendererContainer.style.flexDirection = 'column';
        rendererContainer.style.alignItems = 'center';
        rendererContainer.style.padding = '20px';
        rendererContainer.style.boxSizing = 'border-box';
        rendererContainer.style.width = '100%';
        rendererContainer.style.height = '100%';
        rendererContainer.style.fontFamily = "'Inter', sans-serif";


        titleElement = document.createElement('h1');
        // Styles for titleElement
        titleElement.textContent = 'Connect Four';
        titleElement.style.fontSize = '1.875rem'; // text-3xl
        titleElement.style.fontWeight = 'bold';
        titleElement.style.marginBottom = '1rem'; // mb-4
        titleElement.style.textAlign = 'center';
        titleElement.style.color = '#2563eb'; // blue-600
        rendererContainer.appendChild(titleElement);

        boardElement = document.createElement('div');
        // Styles for boardElement
        boardElement.style.backgroundColor = '#3b82f6'; // blue-500
        boardElement.style.padding = '10px';
        boardElement.style.borderRadius = '10px';
        boardElement.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';
        boardElement.style.display = 'grid';
        boardElement.style.gap = '5px';
        boardElement.style.width = 'auto';
        boardElement.style.maxWidth = '90vw';
        boardElement.style.maxHeight = 'calc(90vh - 120px)';
        boardElement.style.aspectRatio = `${cols} / ${rows}`;
        boardElement.style.marginBottom = '20px';
        rendererContainer.appendChild(boardElement);

        const statusContainer = document.createElement('div');
        // Styles for statusContainer
        statusContainer.style.padding = '10px 15px';
        statusContainer.style.backgroundColor = 'white';
        statusContainer.style.borderRadius = '8px';
        statusContainer.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
        statusContainer.style.textAlign = 'center';
        statusContainer.style.width = 'auto';
        statusContainer.style.maxWidth = '90vw';

        statusTextElement = document.createElement('p');
        // Styles for statusTextElement
        statusTextElement.style.fontSize = '1.1rem';
        statusTextElement.style.fontWeight = '600';

        winnerTextElement = document.createElement('p');
        // Styles for winnerTextElement
        winnerTextElement.style.fontSize = '1.25rem';
        winnerTextElement.style.fontWeight = '700';
        winnerTextElement.style.marginTop = '5px';

        statusContainer.appendChild(statusTextElement);
        statusContainer.appendChild(winnerTextElement);
        rendererContainer.appendChild(statusContainer);

        parentElement.appendChild(rendererContainer);
    }

    if (boardElement.children.length !== rows * cols ||
        boardElement.style.gridTemplateColumns !== `repeat(${cols}, 1fr)` ||
        boardElement.style.gridTemplateRows !== `repeat(${rows}, 1fr)`) {
        boardElement.innerHTML = '';
        boardElement.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
        boardElement.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const cell = document.createElement('div');
                // Styles for cell
                cell.style.backgroundColor = '#f3f4f6'; // gray-100 (empty)
                cell.style.borderRadius = '50%';
                cell.style.display = 'flex';
                cell.style.alignItems = 'center';
                cell.style.justifyContent = 'center';
                cell.style.transition = 'background-color 0.3s';
                // Cell width/height will be determined by the grid
                boardElement.appendChild(cell);
            }
        }
    }
    // Ensure message box is created (it's appended to body, so check separately)
    if (!messageBoxElement && document.body) {
        showMessage("Renderer initialized."); // Call showMessage to create it
    }
    return true;
}

function renderBoardDisplay(gameState, rows, cols) {
    if (!boardElement || !statusTextElement || !winnerTextElement) {
        console.error("ConnectFourRenderer: Renderer DOM elements not initialized.");
        return;
    }
    if (!gameState || typeof gameState.board !== 'object') {
        console.error("ConnectFourRenderer: Invalid gameState or board data", gameState);
        showMessage("Error: Could not load board data. Ensure 'board' is an array.", 'error');
        statusTextElement.textContent = "Error loading game state.";
        return;
    }

    const { board, current_player, is_terminal, winner } = gameState;
    const cells = boardElement.children;

    if (cells.length !== rows * cols) {
        console.error("ConnectFourRenderer: Cell count mismatch. Re-initialization might be needed.");
        return;
    }

    for (let r_json = 0; r_json < rows; r_json++) {
        const jsonRow = board[r_json];
        if (!jsonRow || jsonRow.length !== cols) {
            console.warn(`ConnectFourRenderer: Invalid row data at JSON row index ${r_json}:`, jsonRow);
            const r_visual = (rows - 1) - r_json;
            for (let c_fill = 0; c_fill < cols; c_fill++) {
                const cellIndex = r_visual * cols + c_fill;
                if(cells[cellIndex]) {
                    cells[cellIndex].style.backgroundColor = '#f3f4f6'; // Reset to empty
                }
            }
            continue;
        }
        const r_visual = (rows - 1) - r_json;
        for (let c_json = 0; c_json < cols; c_json++) {
            const cellValue = jsonRow[c_json];
            const cellIndex = r_visual * cols + c_json;
            const cellElement = cells[cellIndex];

            if (!cellElement) continue;

            // Reset to empty cell color first
            cellElement.style.backgroundColor = '#f3f4f6'; // gray-100

            if (cellValue === 'x' || cellValue === 'X') {
                cellElement.style.backgroundColor = '#ef4444'; // red-500
            } else if (cellValue === 'o' || cellValue === 'O') {
                cellElement.style.backgroundColor = '#facc15'; // yellow-400
            }
        }
    }

    statusTextElement.textContent = '';
    winnerTextElement.textContent = '';
    // Clear existing spans if any
    statusTextElement.innerHTML = '';
    winnerTextElement.innerHTML = '';


    if (is_terminal) {
        statusTextElement.textContent = "Game Over!";
        if (winner) {
            if (String(winner).toLowerCase() === 'draw') {
                winnerTextElement.textContent = "It's a Draw!";
            } else {
                const winnerDisplay = String(winner).toUpperCase();
                const playerColor = String(winner).toLowerCase() === 'x' ? '#ef4444' : '#ca8a04';
                winnerTextElement.innerHTML = `Player <span style="color: ${playerColor}; font-weight: bold;">${winnerDisplay}</span> Wins!`;
            }
        } else {
             winnerTextElement.textContent = "Game ended.";
        }
    } else {
        if (current_player) {
            const playerDisplay = String(current_player).toUpperCase();
            const playerColor = String(current_player).toLowerCase() === 'x' ? '#ef4444' : '#ca8a04';
            statusTextElement.innerHTML = `Current Player: <span style="color: ${playerColor}; font-weight: bold;">${playerDisplay}</span>`;
        } else {
            statusTextElement.textContent = "Waiting for player...";
        }
    }
}

// --- Main Renderer Function (Kaggle Environment Interface) ---
function renderer(options) {
    const { environment, step, parent, interactive, isInteractive } = options;

    if (!environment || !environment.steps || !environment.steps[step] ||
        !environment.steps[step][0] || !environment.steps[step][0].observation) {
        console.error("ConnectFourRenderer: Invalid environment structure or step data:", options);
        // Attempt to display error in parent if possible, otherwise log
        if (parent && typeof parent.innerHTML !== 'undefined') {
            parent.innerHTML = "<p style='color:red; font-family: sans-serif;'>Error: Invalid environment data received by renderer.</p>";
        }
        return;
    }

    // For this OpenSpiel Connect Four, dimensions are fixed.
    const rows = DEFAULT_NUM_ROWS;
    const cols = DEFAULT_NUM_COLS;

    if (!ensureRendererElements(parent, rows, cols)) {
        // If parent was null and we couldn't create elements, bail.
        return;
    }

    let gameSpecificState;
    const observation = environment.steps[step][0].observation;

    if (observation && typeof observation.json === 'string') {
        try {
            gameSpecificState = JSON.parse(observation.json);
        } catch (e) {
            console.error("ConnectFourRenderer: Failed to parse game state JSON from observation.json:", e, observation.json);
            showMessage("Error: Invalid game state format (observation.json).", 'error');
            if (statusTextElement) statusTextElement.textContent = "Error: Invalid game state format.";
            return;
        }
    } else if (observation && typeof observation.board === 'object') {
        // If the observation itself is the parsed JSON structure from the proxy
        gameSpecificState = observation;
    } else {
        console.error("ConnectFourRenderer: Game state JSON not found in observation.json or observation.board.", observation);
        showMessage("Error: Game state data not found.", 'error');
        if (statusTextElement) statusTextElement.textContent = "Error: Game state data not found.";
        return;
    }

    renderBoardDisplay(gameSpecificState, rows, cols);

    // Interactive part (not used for display, but good to keep structure)
    // Example: if you had a canvas for clicks
    // if (interactive && parent.querySelector("canvas")) {
    //    parent.querySelector("canvas").style.cursor = isInteractive() ? "pointer" : "default";
    // }
}

// --- Post Ready Message ---
// Inform the parent that the renderer is ready to receive messages/calls.
if (window.parent !== window) {
    window.parent.postMessage({ type: "rendererReady" }, "*");
} else {
    // Standalone mode (e.g. if you open the JS file directly in a test HTML page)
    console.log("Connect Four Renderer: Standalone mode. Call renderer(options) with test data.");
    // For a quick visual check in a test HTML, you might do:
    // document.addEventListener('DOMContentLoaded', () => {
    //     if (ensureRendererElements(document.body, DEFAULT_NUM_ROWS, DEFAULT_NUM_COLS)) {
    //          renderBoardDisplay({
    //             board: Array(DEFAULT_NUM_ROWS).fill(null).map(() => Array(DEFAULT_NUM_COLS).fill('.')),
    //             current_player: 'x',
    //             is_terminal: false,
    //             winner: null
    //         }, DEFAULT_NUM_ROWS, DEFAULT_NUM_COLS);
    //         if(statusTextElement) statusTextElement.textContent = "Standalone mode. Initial empty board.";
    //     }
    // });
}

/**
 * ARE Frontend Application
 * Handles SSE streaming, HITL interactions, and UI updates
 */

class AREApp {
    constructor() {
        this.sessionId = null;
        this.eventSource = null;
        this.nodes = [
            'node_0', 'node_0_confirmation', 'node_1', 'node_2', 'node_3',
            'node_4', 'node_5', 'node_6', 'node_7', 'node_8'
        ];

        this.init();
    }

    init() {
        // DOM Elements
        this.elements = {
            form: document.getElementById('researchForm'),
            questionInput: document.getElementById('questionInput'),
            submitBtn: document.getElementById('submitBtn'),
            globalStatus: document.getElementById('globalStatus'),
            graphSection: document.getElementById('graphSection'),
            currentNodeLabel: document.getElementById('currentNodeLabel'),

            // Reasoning Logic
            reasoningSection: document.getElementById('reasoningSection'),
            reasoningContent: document.getElementById('reasoningContent'),

            // HITL Logic
            hitlModal: document.getElementById('hitlModal'),
            modalNodeBadge: document.getElementById('modalNodeBadge'),
            modalTitle: document.getElementById('modalTitle'),
            modalBody: document.getElementById('modalBody'),
            feedbackWrapper: document.getElementById('feedbackWrapper'),
            feedbackInput: document.getElementById('feedbackInput'),
            approveBtn: document.getElementById('approveBtn'),
            rejectBtn: document.getElementById('rejectBtn'),
            approveBtnText: document.getElementById('approveBtnText'),
            rejectBtnText: document.getElementById('rejectBtnText'),

            resultsSection: document.getElementById('resultsSection'),
            verdictValue: document.getElementById('verdictValue'),
            confidenceValue: document.getElementById('confidenceValue'),
            markdownContent: document.getElementById('markdownContent'),
            jsonContent: document.getElementById('jsonContent'),
            logsSection: document.getElementById('logsSection'),
            logsContainer: document.getElementById('logsContainer')
        };

        // Event Listeners
        this.elements.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.elements.approveBtn.addEventListener('click', () => this.handleApproval('approve'));
        // Reject button acts as "Refine" in confirmation mode
        this.elements.rejectBtn.addEventListener('click', () => this.handleApproval('refine'));

        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
    }

    async handleSubmit(e) {
        e.preventDefault();

        const question = this.elements.questionInput.value.trim();
        if (!question) return;

        // Disable form
        this.elements.submitBtn.disabled = true;
        this.elements.questionInput.disabled = true;

        // Update status
        this.updateGlobalStatus('running');

        // Show sections
        this.elements.graphSection.style.display = 'block';
        this.elements.reasoningSection.style.display = 'block';
        this.elements.reasoningContent.innerHTML = '<div class="reasoning-placeholder">Waiting for agent thought process...</div>';
        this.elements.logsSection.style.display = 'block';
        this.elements.resultsSection.style.display = 'none';

        // Reset nodes
        this.resetNodes();

        // Log start
        this.addLog('Starting research...', 'node');

        try {
            // Start research
            const response = await fetch('/api/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });

            const data = await response.json();
            this.sessionId = data.session_id;

            this.addLog(`Session started: ${this.sessionId}`, 'node');

            // Connect to SSE
            this.connectSSE();

        } catch (error) {
            this.addLog(`Error: ${error.message}`, 'error');
            this.updateGlobalStatus('error');
            this.elements.submitBtn.disabled = false;
            this.elements.questionInput.disabled = false;
        }
    }

    connectSSE() {
        this.eventSource = new EventSource(`/api/events/${this.sessionId}`);

        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleEvent(data);
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.eventSource.close();
        };
    }


    // ... (previous code) ...

    handleEvent(event) {
        switch (event.type) {
            case 'start':
                this.addLog(event.message, 'node');
                break;

            case 'node_reasoning':
                this.updateReasoning(event.reasoning);
                break;

            case 'node_complete':
                this.markNodeComplete(event.node);

                // Special handling for NODE-0 completion to show analysis
                if (event.node === 'node_0' && event.payload) {
                    this.showNode0Output(event.payload);
                }

                // Show API Warnings if any
                if (event.payload && event.payload.api_warnings && event.payload.api_warnings.length > 0) {
                    event.payload.api_warnings.forEach(warning => {
                        this.addLog(`⚠️ ${warning}`, 'error');
                        this.showToast(warning, 'warning');
                    });
                }

                this.addLog(`Completed: ${this.getNodeName(event.node)}`, 'node');
                break;

            case 'hitl_required':
                // Check if this is the NODE-0 confirmation
                if (event.node === 'node_0_confirmation') {
                    // Show analysis UI if payload exists (should come from HITL event too)
                    if (event.payload) {
                        this.showNode0Output(event.payload);
                    }
                    this.addLog(`Waiting for user confirmation...`, 'hitl');
                } else {
                    this.showHITLModal(event);
                    this.addLog(`HITL Required at ${event.node}`, 'hitl');
                }

                // Ensure node is marked as waiting
                const nodeWaiting = document.querySelector(`[data-node="${event.node}"]`);
                if (nodeWaiting) {
                    nodeWaiting.classList.remove('active');
                    nodeWaiting.classList.add('waiting');
                }
                break;

            case 'hitl_resolved':
                this.hideHITLModal();
                // Hide Node-0 output if it was the confirmation
                if (event.node === 'node_0_confirmation') {
                    document.getElementById('node0OutputSection').style.display = 'none';
                }
                this.addLog(`HITL Approved: ${event.node}`, 'hitl');
                break;

            case 'experiment_code_generated':
                this.showExperimentCode(event.payload);
                this.addLog(`Experiment code generated`, 'node');
                break;

            case 'complete':
                this.handleComplete(event);
                this.addLog(`Research complete! Verdict: ${event.verdict}`, 'complete');
                break;

            case 'error':
                this.addLog(`Error: ${event.message}`, 'error');
                this.updateGlobalStatus('error');
                break;
        }
    }

    showNode0Output(payload) {
        const section = document.getElementById('node0OutputSection');

        // Populate fields
        document.getElementById('normalizedQuestion').textContent = payload.normalized_question || '---';

        // Intent
        const intentEl = document.getElementById('researchIntent');
        intentEl.textContent = payload.research_intent || 'Unknown';
        intentEl.className = 'analysis-tag'; // Reset class

        // Confidence
        const confidence = payload.intent_confidence || 0;
        const confPercent = (confidence * 100).toFixed(0) + '%';
        document.getElementById('confidenceValue').textContent = confPercent;
        document.getElementById('confidenceBar').style.width = confPercent;
        document.getElementById('confidenceBar').style.setProperty('--confidence', confPercent);

        document.getElementById('autonomyLevel').textContent = (payload.autonomy_level || '').replace('_', ' ');
        document.getElementById('evidenceThreshold').textContent = (payload.evidence_threshold || '').replace(/_/g, ' ');

        // Variables
        const vars = payload.variables || {};
        this.renderList('independentVars', vars.independent);
        this.renderList('dependentVars', vars.dependent);
        this.renderList('controlVars', vars.control);

        // Show section
        section.style.display = 'block';
        section.scrollIntoView({ behavior: 'smooth' });

        // Bind actions
        document.getElementById('continueResearchBtn').onclick = () => this.handleNode0Confirmation('approve');
        document.getElementById('requestChangesBtn').onclick = () => this.handleNode0Confirmation('refine');
    }

    renderList(elementId, items) {
        const ul = document.getElementById(elementId);
        ul.innerHTML = '';
        if (items && items.length > 0) {
            items.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                ul.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'None identified';
            li.style.fontStyle = 'italic';
            li.style.opacity = '0.5';
            ul.appendChild(li);
        }
    }

    async handleNode0Confirmation(action) {
        if (!this.sessionId) return;

        // In AROS flow, NODE-0 confirmation is a specific HITL step
        // We use the same approval endpoint

        let payload = { action: 'approve' };

        if (action === 'refine') {
            const feedback = prompt("Please enter your changes or clarifications:");
            if (!feedback) return;
            payload = {
                action: 'refine',
                feedback: feedback
            };
        }

        // Disable buttons
        document.getElementById('continueResearchBtn').disabled = true;
        document.getElementById('requestChangesBtn').disabled = true;

        try {
            await fetch(`/api/approve/${this.sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            // Hide section on approve, keep open on refine?
            // actually backend will re-run node-0 if refined
            if (action === 'approve') {
                document.getElementById('node0OutputSection').style.borderLeft = '4px solid var(--accent-green)';
                // Don't hide immediately, let user see it was approved?
                // Or hide to clear clutter. Let's hide after a moment.
                setTimeout(() => {
                    document.getElementById('node0OutputSection').style.display = 'none';
                }, 1500);
            } else {
                this.addLog("Requesting changes...", 'hitl');
            }

        } catch (error) {
            this.addLog(`Confirmation error: ${error.message}`, 'error');
            // Re-enable buttons
            document.getElementById('continueResearchBtn').disabled = false;
            document.getElementById('requestChangesBtn').disabled = false;
        }
    }

    showExperimentCode(payload) {
        const section = document.getElementById('experimentSection');

        // Render instructions
        const instructionsMd = payload.instructions || "Run the code below.";
        document.getElementById('experimentInstructions').innerHTML = this.renderMarkdown(instructionsMd);

        // Render code
        document.getElementById('experimentCode').textContent = payload.code || "# No code generated";

        // Show section
        section.style.display = 'block';
        section.scrollIntoView({ behavior: 'smooth' });

        // Output submit handler
        document.getElementById('submitResultsBtn').onclick = () => this.handleSubmitResults();

        // Copy button
        document.getElementById('copyCodeBtn').onclick = () => {
            navigator.clipboard.writeText(payload.code);
            const btn = document.getElementById('copyCodeBtn');
            btn.textContent = "✓ Copied";
            setTimeout(() => btn.textContent = "📋 Copy", 2000);
        };
    }

    async handleSubmitResults() {
        if (!this.sessionId) return;

        // Mock result submission dialog for now
        // In real app, this might be a file upload or JSON input
        // For AROS, we'll ask for JSON input

        const resultInput = prompt("Please paste the JSON output from your experiment execution:");
        if (!resultInput) return;

        let results;
        try {
            results = JSON.parse(resultInput);
        } catch (e) {
            alert("Invalid JSON. Please ensure you paste valid JSON output.");
            return;
        }

        try {
            const btn = document.getElementById('submitResultsBtn');
            btn.disabled = true;
            btn.innerHTML = '<span>⏳ Submitting...</span>';

            await fetch(`/api/submit-results/${this.sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results: results })
            });

            this.addLog("Experiment results submitted", 'hitl');

            // Hide section
            setTimeout(() => {
                document.getElementById('experimentSection').style.display = 'none';
            }, 1000);

        } catch (error) {
            this.addLog(`Submission error: ${error.message}`, 'error');
            document.getElementById('submitResultsBtn').disabled = false;
        }
    }

    // ... (rest of the class) ...


    updateReasoning(text) {
        if (!text) return;
        // Check if placeholder exists
        const placeholder = this.elements.reasoningContent.querySelector('.reasoning-placeholder');
        if (placeholder) placeholder.remove();

        // Append new reasoning block
        const block = document.createElement('div');
        block.className = 'reasoning-block';
        block.innerHTML = `
            <span class="reasoning-time">[${new Date().toLocaleTimeString()}]</span>
            <span class="reasoning-text">${text}</span>
        `;
        this.elements.reasoningContent.appendChild(block);
        this.elements.reasoningContent.scrollTop = this.elements.reasoningContent.scrollHeight;
    }

    markNodeComplete(nodeName) {
        const nodeEl = document.querySelector(`[data-node="${nodeName}"]`);
        if (nodeEl) {
            nodeEl.classList.remove('active', 'waiting');
            nodeEl.classList.add('completed');
        }

        // Mark next node as active
        const nodeIndex = this.nodes.indexOf(nodeName);
        if (nodeIndex < this.nodes.length - 1) {
            const nextNode = document.querySelector(`[data-node="${this.nodes[nodeIndex + 1]}"]`);
            if (nextNode) {
                nextNode.classList.add('active');
            }
        }
    }

    showHITLModal(event) {
        const payload = event.payload || {};
        const nodeName = event.node;

        this.elements.modalNodeBadge.textContent = this.getNodeName(nodeName).toUpperCase();

        // RESET STATE
        this.elements.feedbackWrapper.style.display = 'none';
        this.elements.feedbackInput.value = '';
        this.hitlType = payload.type || 'approval'; // Store type for handling

        if (payload.type === 'confirmation') {
            // CONFIRMATION MODE (Node-0)
            this.elements.modalTitle.textContent = "🛡️ Research Scope Confirmation";
            this.elements.modalBody.innerHTML = `
                <div class="confirmation-details">
                    <p><strong>Proposed Question:</strong><br>${payload.normalized_question}</p>
                    <p><strong>Intent:</strong> <span class="badge ${payload.research_intent}">${payload.research_intent}</span></p>
                    <p><strong>Variables:</strong> IV: [${payload.variables?.independent?.join(', ')}] | DV: [${payload.variables?.dependent?.join(', ')}]</p>
                    <div class="reasoning-summary">
                        <strong>Agent Reasoning:</strong>
                        <p>${payload.reasoning || "No reasoning provided."}</p>
                    </div>
                </div>
            `;
            this.elements.approveBtnText.textContent = "✓ Proceed";
            this.elements.rejectBtnText.textContent = "✎ Refine";

            // Refine button logic handled in click handler via "refine" action
            // But we need to toggle feedback input on 'reject'/refine click? 
            // Actually, let's show input when they click refine? 
            // Or just always show it for refinement?
            // Let's make the Refine button toggle the input, and then change to "Submit Refinement"

            this.elements.feedbackWrapper.style.display = 'block'; // Always show feedback input option? 
            // Better UX: "Proceed" ignores input. "Refine" uses input.
            // If input is empty, "Refine" warns?

        } else {
            // APPROVAL MODE (Node-4/7)
            this.elements.modalTitle.textContent = "👤 Human Approval Required";
            this.elements.modalBody.innerHTML = `
                <div class="contract-summary">
                    <p><strong>Summary:</strong> ${payload.contract_summary}</p>
                    <p><strong>Tasks:</strong> ${payload.tasks_count || 0} tasks</p>
                    <div class="cost-estimate">
                        <span class="cost-label">Estimated Cost:</span>
                        <span class="cost-value">${payload.cost_estimate?.compute_hours || 'Low'} (dry run)</span>
                    </div>
                </div>
            `;
            this.elements.approveBtnText.textContent = "✓ Approve";
            this.elements.rejectBtnText.textContent = "✕ Reject";
            this.elements.feedbackWrapper.style.display = 'none';
        }

        this.elements.hitlModal.style.display = 'flex';

        // Mark node as waiting
        const nodeEl = document.querySelector(`[data-node="${event.node}"]`);
        if (nodeEl) nodeEl.classList.add('waiting');
    }

    hideHITLModal() {
        this.elements.hitlModal.style.display = 'none';
    }

    async handleApproval(actionType) {
        if (!this.sessionId) return;

        let finalAction = 'approve'; // default API expectation
        let feedback = null;

        if (this.hitlType === 'confirmation') {
            if (actionType === 'approve') {
                finalAction = 'approve';
            } else {
                // Refine
                finalAction = 'refine';
                feedback = this.elements.feedbackInput.value.trim();
                if (!feedback && actionType === 'refine') {
                    alert("Please provide feedback to refine the plan.");
                    return;
                }
            }
        } else {
            // Standard Approval
            finalAction = actionType === 'approve' ? 'approve' : 'reject';
            // Logic for Node-7 loop handled in backend based on "approve" (continue) vs "reject" (terminate) ??
            // api.py handles: if node_7: approve -> continue, else -> terminate? 
            // Wait, api.py: "continue" if request.action == "approve" else "terminate"
        }

        try {
            await fetch(`/api/approve/${this.sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: finalAction,
                    feedback: feedback
                })
            });

        } catch (error) {
            this.addLog(`Approval error: ${error.message}`, 'error');
        }
    }

    async handleComplete(event) {
        // Close SSE
        if (this.eventSource) {
            this.eventSource.close();
        }

        // Update status
        this.updateGlobalStatus('ready');
        if (this.elements.currentNodeLabel) {
            this.elements.currentNodeLabel.textContent = 'Research Complete!';
        }

        // Re-enable form
        this.elements.submitBtn.disabled = false;
        this.elements.questionInput.disabled = false;

        // Fetch full report
        try {
            const response = await fetch(`/api/report/${this.sessionId}`);
            const report = await response.json();

            // Update results
            this.elements.verdictValue.textContent = report.verdict || 'Unknown';
            this.elements.verdictValue.className = `verdict-value ${(report.verdict || '').toLowerCase()}`;

            this.elements.confidenceValue.textContent =
                typeof report.confidence === 'number'
                    ? (report.confidence * 100).toFixed(0) + '%'
                    : report.confidence || '---';

            // Render markdown
            this.elements.markdownContent.innerHTML = this.renderMarkdown(report.markdown || '');

            // Render JSON
            this.elements.jsonContent.textContent = JSON.stringify(report.json || {}, null, 2);

            // Show results
            this.elements.resultsSection.style.display = 'block';

            // Scroll to results
            this.elements.resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            this.addLog(`Report fetch error: ${error.message}`, 'error');
        }
    }

    renderMarkdown(md) {
        // Simple markdown rendering
        return md
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/\n/gim, '<br>')
            .replace(/\| (.*) \|/gim, (match) => {
                const cells = match.split('|').filter(c => c.trim());
                return `<tr>${cells.map(c => `<td>${c.trim()}</td>`).join('')}</tr>`;
            });
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${type === 'error' ? '🚫' : (type === 'warning' ? '⚠️' : 'ℹ️')}</span>
                <span class="toast-message">${message}</span>
            </div>
        `;
        document.body.appendChild(toast);

        // Simple animation
        requestAnimationFrame(() => toast.classList.add('show'));

        // Remove after 5s
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    resetNodes() {
        document.querySelectorAll('.node').forEach(node => {
            node.classList.remove('active', 'completed', 'waiting');
        });
        // Mark first node as active
        document.querySelector('[data-node="node_0"]')?.classList.add('active');
        if (this.elements.currentNodeLabel) {
            this.elements.currentNodeLabel.textContent = 'Starting...';
        }
    }

    getNodeName(nodeId) {
        const names = {
            'node_0': 'Intake',
            'node_0_confirmation': 'Confirm',
            'node_1': 'Router',
            'node_2': 'Evidence',
            'node_3': 'Contract',
            'node_4': 'HITL-1',
            'node_5': 'Worker',
            'node_6': 'Critic',
            'node_7': 'HITL-2',
            'node_8': 'Report'
        };
        return names[nodeId] || nodeId;
    }

    updateGlobalStatus(status) {
        this.elements.globalStatus.className = `status-badge ${status}`;
        const statusText = {
            'ready': 'Ready',
            'running': 'Running',
            'error': 'Error'
        };
        this.elements.globalStatus.querySelector('.status-text').textContent = statusText[status] || status;
    }

    addLog(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        this.elements.logsContainer.appendChild(entry);
        this.elements.logsContainer.scrollTop = this.elements.logsContainer.scrollHeight;
    }

    switchTab(tabName) {
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `${tabName}Panel`);
        });
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.areApp = new AREApp();
});

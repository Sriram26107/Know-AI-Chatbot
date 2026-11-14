document.addEventListener("DOMContentLoaded", () => {
    const $ = id => document.getElementById(id);

    const chatList = $("chatList");
    const chatBox = $("chatBox");
    const messageInput = $("messageInput");
    const sendButton = $("sendButton");
    const welcomeScreen = $("welcomeScreen");
    const loadingIndicator = $("loadingIndicator");
    const documentInput = $("documentInput");

    let currentChatId = null;
    let chats = [];
    let pendingFile = null;
    let isSending = false;
    let isLoadingChat = false;

    const DEFAULT_FILE_PROMPT =
        "Please read the uploaded document and give me a clear summary of its important information.";

    const API = {
        chats: "/auth/my-chats",
        createChat: "/chats",
        messages: id => `/chats/${id}/messages`,
        saveUserMessage: id => `/chats/${id}/messages/user`,
        generateResponse: (chatId, messageId) =>
            `/chats/${chatId}/messages/${messageId}/response`,
        deleteChat: id => `/chats/${id}`,
        upload: "/upload-test",
        documents: "/documents",
        deleteDocument: id => `/documents/${id}`
    };

    // Authentication and API requests

    function getToken() {
        return localStorage.getItem("access_token");
    }

    async function apiFetch(url, options = {}) {
        const headers = { ...(options.headers || {}) };
        const token = getToken();

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            ...options,
            headers
        });

        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
            ? await response.json()
            : await response.text();

        if (response.status === 401) {
            localStorage.removeItem("access_token");
            window.location.href = "/login";
            throw new Error("Session expired. Please log in again.");
        }

        if (!response.ok) {
            throw new Error(
                typeof data === "object"
                    ? data.message || data.error || `Error ${response.status}`
                    : data || `Error ${response.status}`
            );
        }

        return data;
    }

    function getMessageId(result) {
        return (
            result?.chat_message?.id ??
            result?.message?.id ??
            result?.user_message?.id ??
            result?.message_id ??
            result?.id ??
            null
        );
    }

    function getAssistantContent(result) {
        return (
            result?.chat_message?.content ??
            result?.assistant_message?.content ??
            result?.message?.content ??
            result?.response ??
            result?.content ??
            ""
        );
    }

    // Status and loading

    function setStatus(element, message, type = "") {
        if (!element) return;

        element.textContent = message;
        element.className = "status-message";

        if (type) {
            element.classList.add(`status-${type}`);
        }
    }

    function setLoading(show) {
        if (loadingIndicator) {
            loadingIndicator.hidden = !show;
        }
    }

    function updateWelcome() {
        if (!welcomeScreen || !chatBox) return;
        welcomeScreen.hidden = chatBox.children.length > 0;
    }

    function scrollBottom() {
        const area = $("conversationArea");
        if (area) {
            area.scrollTop = area.scrollHeight;
        }
    }

    // Pending attachment preview

    function createAttachmentPreview() {
        if ($("pendingAttachment")) return;

        const composer = document.querySelector(".composer");
        if (!composer) return;

        const preview = document.createElement("div");
        preview.id = "pendingAttachment";
        preview.className = "pending-attachment";
        preview.hidden = true;

        preview.innerHTML = `
            <span class="pending-file-icon">▤</span>
            <div class="pending-file-info">
                <strong id="pendingFileName"></strong>
                <small>Ready to send</small>
            </div>
            <button type="button"
                    id="removeAttachmentButton"
                    title="Remove attachment">✕</button>
        `;

        composer.parentNode.insertBefore(preview, composer);

        $("removeAttachmentButton").addEventListener(
            "click",
            removePendingFile
        );
    }

    function showPendingFile(file) {
        createAttachmentPreview();

        const preview = $("pendingAttachment");
        if (!preview) return;

        $("pendingFileName").textContent = file.name;
        preview.hidden = false;
    }

    function removePendingFile() {
        pendingFile = null;

        if (documentInput) {
            documentInput.value = "";
        }

        const preview = $("pendingAttachment");
        if (preview) {
            preview.hidden = true;
        }
    }

    // Document attachment card

    function addDocumentCard(doc, messageBody) {
        if (!doc || !doc.id || !messageBody) return;

        if ($(`document-card-${doc.id}`)) return;

        const card = document.createElement("div");
        card.id = `document-card-${doc.id}`;
        card.className = "document-message-card";

        const icon = document.createElement("span");
        icon.className = "document-message-icon";
        icon.textContent = "▤";

        const info = document.createElement("div");
        info.className = "document-message-info";

        const name = document.createElement("strong");
        name.textContent = doc.filename || "Uploaded document";

        const label = document.createElement("small");
        label.textContent = "Uploaded document";

        info.append(name, label);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "✕";
        remove.title = "Delete document";
        remove.setAttribute("aria-label", "Delete uploaded document");

        remove.addEventListener("click", async () => {
            if (!confirm(`Delete ${doc.filename || "this document"}?`)) {
                return;
            }

            remove.disabled = true;

            try {
                await apiFetch(API.deleteDocument(doc.id), {
                    method: "DELETE"
                });

                card.remove();

                setStatus(
                    $("uploadStatus"),
                    "Document deleted successfully.",
                    "success"
                );
            } catch (error) {
                remove.disabled = false;
                alert(error.message);
            }
        });

        card.append(icon, info, remove);

        const attachments = messageBody.querySelector(".message-attachments");

        if (attachments) {
            attachments.appendChild(card);
        } else {
            const container = document.createElement("div");
            container.className = "message-attachments";
            container.appendChild(card);
            messageBody.appendChild(container);
        }
    }

    // Message rendering

    function addMessage(role, content, messageId = null, documents = []) {
        const message = document.createElement("div");
        message.className = `message ${role}`;

        if (messageId !== null) {
            message.dataset.messageId = messageId;
        }

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "assistant" ? "✦" : "U";

        const body = document.createElement("div");
        body.className = "message-content";

        const text = document.createElement("div");
        text.className = "message-text";
        text.textContent = content || "";

        body.appendChild(text);

        if (role === "assistant") {
            const actions = document.createElement("div");
            actions.className = "message-actions";

            const copy = document.createElement("button");
            copy.type = "button";
            copy.textContent = "Copy";

            copy.addEventListener("click", async () => {
                try {
                    await navigator.clipboard.writeText(content || "");
                    copy.textContent = "Copied";

                    setTimeout(() => {
                        copy.textContent = "Copy";
                    }, 1200);
                } catch {
                    copy.textContent = "Copy unavailable";
                }
            });

            actions.appendChild(copy);
            body.appendChild(actions);
        }

        message.append(avatar, body);
        chatBox.appendChild(message);

        if (Array.isArray(documents)) {
            documents.forEach(doc => addDocumentCard(doc, body));
        }

        updateWelcome();
        scrollBottom();

        return message;
    }

    // Hide the old bottom documents panel

    function hideDocumentsPanel() {
        const panel = document.querySelector(".documents-panel");

        if (panel) {
            panel.hidden = true;
        }
    }

    // Sidebar chat list

    function renderChats() {
        if (!chatList) return;

        chatList.innerHTML = "";

        chats.forEach(chat => {
            const item = document.createElement("div");
            item.className = "chat-item";

            if (String(chat.id) === String(currentChatId)) {
                item.classList.add("active");
            }

            const title = document.createElement("span");
            title.className = "chat-item-title";
            title.textContent = chat.title || "New chat";

            title.addEventListener("click", () => {
                selectChat(chat.id);
            });

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "delete-chat-button";
            deleteButton.textContent = "🗑️";
            deleteButton.title = "Delete chat";

            deleteButton.addEventListener("click", async event => {
                event.stopPropagation();
                await deleteChat(chat.id);
            });

            item.append(title, deleteButton);
            chatList.appendChild(item);
        });
    }

    // Create a chat

    async function createChat() {
        const result = await apiFetch(API.createChat, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: "New chat"
            })
        });

        const chat = result.chat;

        if (!chat || !chat.id) {
            throw new Error("Chat ID was not returned.");
        }

        currentChatId = chat.id;
        chats.unshift(chat);

        chatBox.innerHTML = "";

        renderChats();
        updateWelcome();

        return true;
    }

    // Load documents and connect them to their original messages

    async function loadChatDocuments(chatId) {
        const result = await apiFetch(API.documents);
        const documents = result.documents || [];

        return documents.filter(doc =>
            String(doc.chat_session_id) === String(chatId) &&
            doc.message_id !== null &&
            doc.message_id !== undefined
        );
    }

    // Select and restore an existing conversation

    async function selectChat(id) {
        if (isSending || isLoadingChat) return;

        isLoadingChat = true;
        currentChatId = id;

        chatBox.innerHTML = "";
        renderChats();
        updateWelcome();
        setLoading(true);

        try {
            const [messageResult, documents] = await Promise.all([
                apiFetch(API.messages(id)),
                loadChatDocuments(id)
            ]);

            const messages = messageResult.messages || [];

            const documentsByMessage = new Map();

            documents.forEach(doc => {
                const key = String(doc.message_id);

                if (!documentsByMessage.has(key)) {
                    documentsByMessage.set(key, []);
                }

                documentsByMessage.get(key).push(doc);
            });

            messages.forEach(message => {
                const attachedDocuments =
                    documentsByMessage.get(String(message.id)) ||
                    message.documents ||
                    [];

                addMessage(
                    message.role === "user" ? "user" : "assistant",
                    message.content,
                    message.id,
                    attachedDocuments
                );
            });

            hideDocumentsPanel();
        } catch (error) {
            console.error("Chat selection failed:", error);

            addMessage(
                "assistant",
                `Unable to load this conversation: ${error.message}`
            );
        } finally {
            setLoading(false);
            isLoadingChat = false;
        }

        if (window.innerWidth <= 760) {
            closeSidebar();
        }
    }

    // Load chat list

    async function loadChats() {
        try {
            const result = await apiFetch(API.chats);
            chats = result.chats || [];

            renderChats();

            if (!currentChatId && chats.length > 0) {
                await selectChat(chats[0].id);
            }
        } catch (error) {
            console.error("Chat loading failed:", error);

            setStatus(
                $("documentsStatus"),
                `Unable to load conversations: ${error.message}`,
                "error"
            );
        }
    }

    // Upload the selected document and link it to the user message

    async function uploadDocument(file, messageId) {
        if (!currentChatId) {
            throw new Error("Please create or select a chat first.");
        }

        const formData = new FormData();
        formData.append("file", file);
        formData.append("chat_session_id", currentChatId);
        formData.append("message_id", messageId);

        const result = await apiFetch(API.upload, {
            method: "POST",
            body: formData
        });

        if (!result.document_id) {
            throw new Error("Document ID was not returned.");
        }

        return {
            id: result.document_id,
            filename: result.filename || file.name,
            chat_session_id: result.chat_session_id || currentChatId,
            message_id: result.message_id || messageId
        };
    }

    // Refresh the sidebar after a response

    async function refreshChatList() {
        try {
            const result = await apiFetch(API.chats);
            chats = result.chats || [];
            renderChats();
        } catch (error) {
            console.error("Chat list refresh failed:", error);
        }
    }

    // Send a message and its optional document

    async function sendMessage() {
        if (isSending || isLoadingChat) return;

        const typedMessage = messageInput?.value.trim() || "";
        const file = pendingFile;

        if (!typedMessage && !file) return;

        isSending = true;

        if (sendButton) {
            sendButton.disabled = true;
        }

        setLoading(true);

        const messageToSend = typedMessage || DEFAULT_FILE_PROMPT;

        try {
            if (!currentChatId) {
                await createChat();
            }

            // 1. Save the user's message first.
            const userResult = await apiFetch(
                API.saveUserMessage(currentChatId),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        content: messageToSend
                    })
                }
            );

            const messageId = getMessageId(userResult);

            if (!messageId) {
                throw new Error(
                    "The server did not return the saved user message ID."
                );
            }

            // Display the user's message.
            const userMessageElement = addMessage(
                "user",
                messageToSend,
                messageId
            );

            if (messageInput) {
                messageInput.value = "";
                resizeTextarea();
            }

            // 2. Upload the file and attach it to this message.
            if (file) {
                setStatus(
                    $("uploadStatus"),
                    `Uploading ${file.name}...`
                );

                const uploadedDocument = await uploadDocument(
                    file,
                    messageId
                );

                addDocumentCard(
                    uploadedDocument,
                    userMessageElement.querySelector(".message-content")
                );

                removePendingFile();

                setStatus(
                    $("uploadStatus"),
                    "Document uploaded and attached to your message.",
                    "success"
                );
            }

            // 3. Ask the backend to generate the AI response.
            const responseResult = await apiFetch(
                API.generateResponse(currentChatId, messageId),
                {
                    method: "POST"
                }
            );

            const answer = getAssistantContent(responseResult);

            if (!answer) {
                throw new Error("The AI response was empty.");
            }

            addMessage("assistant", answer);

            if (responseResult.chat?.title) {
                const chat = chats.find(
                    item => String(item.id) === String(currentChatId)
                );

                if (chat) {
                    chat.title = responseResult.chat.title;
                }
            }

            await refreshChatList();
            hideDocumentsPanel();
        } catch (error) {
            console.error("Message sending failed:", error);

            addMessage(
                "assistant",
                `Sorry, something went wrong: ${error.message}`
            );

            setStatus(
                $("uploadStatus"),
                error.message,
                "error"
            );
        } finally {
            isSending = false;

            if (sendButton) {
                sendButton.disabled = false;
            }

            setLoading(false);
            messageInput?.focus();
        }
    }

    // Delete a chat

    async function deleteChat(chatId) {
        const chat = chats.find(
            item => String(item.id) === String(chatId)
        );

        if (!chat) return;

        const confirmed = confirm(
            `Are you sure you want to delete "${chat.title || "New chat"}"?\n\nThis action cannot be undone.`
        );

        if (!confirmed) return;

        if (isSending || isLoadingChat) {
            alert("Please wait until the current operation finishes.");
            return;
        }

        try {
            await apiFetch(API.deleteChat(chatId), {
                method: "DELETE"
            });

            chats = chats.filter(
                item => String(item.id) !== String(chatId)
            );

            if (String(currentChatId) === String(chatId)) {
                currentChatId = null;
                chatBox.innerHTML = "";
                removePendingFile();

                setStatus($("uploadStatus"), "", "");
                updateWelcome();

                if (chats.length > 0) {
                    renderChats();
                    await selectChat(chats[0].id);
                } else {
                    renderChats();
                }
            } else {
                renderChats();
            }

            setStatus(
                $("documentsStatus"),
                "Chat deleted successfully.",
                "success"
            );
        } catch (error) {
            console.error("Chat deletion failed:", error);
            alert(`Unable to delete chat: ${error.message}`);
        }
    }

    // Textarea sizing

    function resizeTextarea() {
        if (!messageInput) return;

        messageInput.style.height = "auto";
        messageInput.style.height =
            Math.min(messageInput.scrollHeight, 170) + "px";
    }

    // Sidebar controls

    function openSidebar() {
        $("sidebar")?.classList.add("open");
        $("sidebarOverlay")?.classList.add("visible");
    }

    function closeSidebar() {
        $("sidebar")?.classList.remove("open");
        $("sidebarOverlay")?.classList.remove("visible");
    }

    // Event listeners

    $("createChatButton")?.addEventListener("click", async () => {
        if (isSending || isLoadingChat) return;

        try {
            currentChatId = null;
            chatBox.innerHTML = "";
            removePendingFile();
            updateWelcome();
            renderChats();
            messageInput?.focus();
        } catch (error) {
            alert(error.message);
        }
    });

    sendButton?.addEventListener("click", sendMessage);

    messageInput?.addEventListener("input", resizeTextarea);

    messageInput?.addEventListener("keydown", event => {
        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.isComposing
        ) {
            event.preventDefault();
            sendMessage();
        }
    });

    $("attachButton")?.addEventListener("click", () => {
        documentInput?.click();
    });

    $("uploadButton")?.addEventListener("click", () => {
        documentInput?.click();
    });

    documentInput?.addEventListener("change", () => {
        const file = documentInput.files?.[0];
        if (!file) return;

        const extension = file.name.split(".").pop().toLowerCase();

        if (!["pdf", "docx", "txt"].includes(extension)) {
            alert("Only PDF, DOCX and TXT files are supported.");
            removePendingFile();
            return;
        }

        pendingFile = file;
        showPendingFile(file);

        setStatus(
            $("uploadStatus"),
            "Document ready. Press the send arrow."
        );
    });

    $("themeButton")?.addEventListener("click", () => {
        document.body.classList.toggle("light-theme");
    });

    $("openSidebar")?.addEventListener("click", openSidebar);
    $("closeSidebar")?.addEventListener("click", closeSidebar);
    $("sidebarOverlay")?.addEventListener("click", closeSidebar);

    $("logoutButton")?.addEventListener("click", () => {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
    });

    $("searchChatsButton")?.addEventListener("click", () => {
        const search = prompt("Search your conversations:");
        if (search === null) return;

        document.querySelectorAll(".chat-item").forEach(item => {
            item.hidden = !item.textContent
                .toLowerCase()
                .includes(search.toLowerCase());
        });
    });

    document.querySelectorAll(".suggestion-card").forEach(card => {
        card.addEventListener("click", () => {
            if (!messageInput) return;

            messageInput.value = card.dataset.prompt || "";
            resizeTextarea();
            messageInput.focus();
        });
    });

    // Initial setup

    if (!getToken()) {
        window.location.href = "/login";
        return;
    }

    createAttachmentPreview();
    hideDocumentsPanel();
    setLoading(false);
    updateWelcome();
    loadChats();
});
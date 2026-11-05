# 🧠 AI Chatbot Platform

A smart, multilingual chatbot developed by **[ESSID Saria]** with **Rasa** and Python, designed for internal use at **[DSI]**.

> ⚠️ **NOTICE**  
> This project is intended **strictly for internal use** within DSI. Unauthorized reproduction, distribution, or reuse—particularly for external, personal, academic, or commercial use—is **prohibited**.

---

## 🛠️ Technologies Used

- **Conversational orchestration:** Rasa
- **Custom actions and routing:** Python
- **Known-question retrieval:** FAISS
- **Complex, document-based questions:** RAG retrieval over PDF documents
- **Deployment:** Docker (where configured)

---

## 🔎 Hybrid Question Answering

The chatbot uses two retrieval paths, selected according to the question:

- **Known questions:** retrieve a matching answer from the FAISS index.
- **Complex questions:** use the RAG service to retrieve relevant context from PDF documents; Rasa then uses that context to prepare the response.

```mermaid
flowchart LR
    User[User] --> Rasa[Rasa chatbot]
    Rasa -->|Known question| FAISS[FAISS known-question index]
    FAISS -->|Retrieved answer| Rasa
    Rasa -->|Complex document question| RAG[RAG service]
    PDFs[PDF knowledge base] --> RAG
    RAG -->|Retrieved context| Rasa
    Rasa -->|Response| User
```

---

## Hybrid Intent Routing

The chatbot routes approximately 83 intents to different response paths:

| Route                   | Intents | Response source                                                                                                 |
|-------------------------|--------:|-----------------------------------------------------------------------------------------------------------------|
| Default                 |       5 | Default conversation handling, including `nlu_fallback`, `affirm_helpful`, `deny_helpful`, `affirm`, and `deny` |
| Easy: candidate results |       6 | Spring Boot services                                                                                            |
| Easy: FAQ               |      22 | Direct semantic search using FAISS                                                                              |
| Exceptions              |      10 | Local PDF or JSON files                                                                                         |
| Hard questions          |      40 | RAG retrieval over Markdown knowledge-base files                                                                |

When a question does not match the FAQ similarity threshold, the conversation is passed to `ActionMaintainConversationFlow` for LLM-based fallback handling.

### Out-of-scope and missing-context behavior

Semantic FAISS threshold is your relevance decision mechanism:
- Similarity score satisfies the threshold → RELATED → continue with the appropriate response route.
- Similarity score does not satisfy the threshold → UNRELATED → invoke solo_feedback().

The fallback prompt includes instructions from `solo_feedback()`.
When a question is unrelated to PGPG, ESPRIT, or DSI—or when the RAG context is empty—the LLM is instructed to explain the chatbot’s scope.
It may provide general information when appropriate, clearly marked as general rather than official PGPG information.
If the user expresses an emotion, the chatbot responds empathetically before explaining its scope.

### Examples

#### Example-1
**User:** Je vais acheter un PC. Quel est le modèle le plus performant ?

**Bot:** Comme votre question porte sur l'achat d'un PC, il s'agit d'un sujet hors contexte du système PGPG ; à titre informatif uniquement (basé sur des connaissances générales et non sur les informations officielles PGPG), les modèles les plus performants actuellement sur le marché sont généralement des stations de travail comme le Dell Precision ou des ordinateurs portables haut de gamme gaming/création comme le ASUS ROG Zephyrus ou le MacBook Pro M3 Max, mais je me limite exclusivement à l'assistance PGPG pour vos passages de grade.

#### Example-2
**User:** donner la mission de ef

**Bot:** En tant que candidat Enseignant Formateur (EF), vos missions consistent à assurer des modules d’enseignement en autonomie, à encadrer des projets étudiants et des stages, à participer à la conception et à l’évaluation des examens, ainsi qu’à contribuer à l’amélioration des contenus pédagogiques, tout en sachant que vous ne gérez pas les sessions.

---

---

## 📌 Project Purpose

This chatbot was developed to:
- Assist employees with real-time, AI-driven support on internal platforms
- Handle multilingual queries (English, Arabic, etc.): To be done in near future
- Automate common FAQ and support tasks
- Serve as an evolving knowledge assistant for the enterprise

---

### Multi-Signal Follow-Up Decision Mechanism

The chatbot uses a **multi-signal decision mechanism** to determine whether a new user question is a contextual follow-up or an independent question.

The decision is not based solely on question length or semantic similarity.

#### 1. Basic Semantic Follow-Up Criterion

The `is_basicfollowup_criteria()` method provides an initial semantic signal:

- Checks whether a previous user question exists.
- Generates embeddings for the current and previous questions.
- Computes their cosine similarity.
- Compares the similarity score against the configured `FOLLOWUP_THRESHOLD`.

This method returns a Boolean indicating whether the questions are sufficiently semantically similar.

**Important:** This is only a basic follow-up criterion. A short question is not automatically considered a follow-up. The previously used short-question heuristic has been deliberately removed to avoid false positives.

#### 2. Multi-Signal Decision Evaluation

The initial semantic result is combined with the broader decision mechanism implemented in `get_decision_infos()`.

The decision process takes into account conversational information, including:

- The current user question.
- The previous user question.
- The current predicted intent.
- The previous intent.
- The decision mode returned by the multi-signal evaluation.

This allows the chatbot to consider the conversational context rather than relying on a single similarity score.

#### 3. Final Follow-Up Action

The `get_forwarded_action()` method combines:

- The basic semantic follow-up criterion.
- The decision mode produced by the multi-signal mechanism.
- The conversation's existing intent and flow information.

Based on this evaluation, the chatbot determines whether to forward the conversation to an appropriate previous action or continue with the normal intent-handling process.

The resulting events are flattened before being returned to Rasa.

#### 4. Expected Behavior

| Scenario                                                          | Expected behavior                                   |
|-------------------------------------------------------------------|-----------------------------------------------------|
| A semantically related question that continues the previous topic | Can be classified as a contextual follow-up         |
| A short question without relevant conversational context          | Must not automatically be classified as a follow-up |
| A question referring to a previous topic using different wording  | Evaluated using the combined decision mechanism     |
| An independent question unrelated to the previous conversation    | Should be handled as a new question                 |

**Design principle:** Semantic similarity provides an initial signal; the final follow-up decision is made through the combined multi-signal mechanism. This separation helps reduce false positives and preserve conversational continuity.

---

## 🔒 Intellectual Property & Usage Policy

This repository is the intellectual property of **[ESSID Saria]**, developed during tenure at **[DSI]**, with clear contributions tracked via Git.

All contributors are allowed to:
- Use this platform for internal purposes only
- Contribute to its improvement under company authorization

You **must not**:
- Reuse the codebase for personal academic projects
- Fork or clone this repository for external use
- Publish this code or its parts on public platforms (e.g., GitHub, GitLab, StackOverflow)
- Share with or sell to third parties

Violations will be reported and may lead to **disciplinary or legal action** depending on the terms of your employment or internship agreement.

---

## 🧾 Author & Ownership

- **Main Developer:** [ESSID Saria] ([saria.essid@esprit.tn])
- **Status:** Sole author and maintainer during initial development (100% commit history)
- **Company:** [ESPRIT-DSI]

---

## 📄 License

This project is licensed under a **Proprietary License**:  
You **cannot** use, copy, modify, merge, publish, distribute, sublicense, or sell copies of this Software or its parts outside the scope of internal enterprise use.

Contact **[ESSID Saria]** or the **IT Department** for special permissions.

---

## 🤝 Contributions

To contribute:
1. Make a new branch from `main`
2. Submit a pull request with a clear explanation
3. Ensure no hardcoded or private data is leaked

> Every contribution is logged and monitored.

---

## 🚀 Future Features

- Full analytics dashboard (employee usage stats)
- GPT-based fallback mode
- French & Arabic deep NLP models
- Customizable component support

---

## 👨‍💻 Author & 🙏 Acknowledgments
- Built with ❤️ by [ESSID Saria] 💻
- Thanks to DevOps Responsible [Seddik Bouzayeni] for the commitment

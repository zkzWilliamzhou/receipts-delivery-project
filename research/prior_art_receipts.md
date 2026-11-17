# Prior-Art and Novelty Validation for an Auditable, Reversible, Claim-Verifying Developer CLI

## Executive summary: the integration is novel even though every layer already exists

No surveyed primary source demonstrates a single local-first developer CLI that simultaneously (a) runs arbitrary shell commands for an AI coding agent in an isolated, reversible, copy-on-write workspace; (b) emits a tamper-evident, hash-chained receipt containing argv, cwd, an env allowlist, stdout/stderr, exit code, before/after filesystem hashes, and wall time; (c) resolves a natural-language work claim such as “tests pass” to a deterministic PASS / FAIL / UNVERIFIED result against those receipts; (d) restores the pre-action state or deterministically replays the action; and (e) enforces a default-deny local least-privilege policy covering network, protected paths, and command allow/deny lists. This combination does not exist as one tool in the evidence reviewed.

The result is best understood as an integration claim, not a breakthrough in any individual technical layer. Kernel and user-space sandboxing, copy-on-write snapshots, content-addressed storage, audit logs, provenance formats, build-execution identities, and agent observability all exist. What the hypothetical tool adds is the claim-to-evidence contract that binds them: a command is intercepted before execution; its pre-state, policy decision, and post-state are recorded as one atomic unit; a verifier maps prose to executable evidence predicates; and the same record supports both proof and rollback.

The strongest counterarguments are that Codex, Claude Code, Cline, or an editor checkpoint already “does this,” or that a backup tool plus Bubblewrap plus an audit log is the same system. Those arguments are rejected in this report, but not with absolute certainty. A Codex-like sandbox supplies (a) and partial (e), while Cursor-like checkpoints and backup tools supply partial (d). None supplies the specified local receipt as an integrated audit and control object, and none of the retrieved documentation shows an explicit receipt schema containing the listed fields.

Agent observability platforms are not serious counterexamples to the core. Langfuse, AgentOps, Braintrust, Weave, and Phoenix can record traces, tool calls, scores, evaluations, datasets, and experiments, but they do not mediate command execution, isolate the shell, snapshot the filesystem, or enforce local command and network policy. [2][3][4][5][6] Their correct role is therefore downstream: they can ingest receipts, never originate trust.

The genuinely novel engineering contribution is the closed loop among policy, capture, state, receipt, and claim semantics. The burden of proof must be met by design artifacts that demonstrate five properties: atomicity across execution and receipt creation; a stated trust model for the kernel, root, TPM or signing key, clock, and receipt store; completeness and liveness of the capture layer; safe reversal; and evidence predicates that distinguish “the agent said the tests passed” from “a test runner emitted a structured pass result.”

## 1. The specification defines five separate technical contracts, not one feature

**The requirement set is deliberately overconstrained, so a fair prior-art review must treat it as a system-level novelty question.** A tool that intercepts commands but only records stdout is not a receipt system. A tool that snapshots state but cannot show what command caused the change is not an audit system. A tool that evaluates model outputs is not an execution verifier unless it can prove that a specified command actually ran under specified constraints and produced the claimed result.

Requirement (a) has at least five distinct subproperties: process isolation, filesystem containment, network containment, reversibility, and copy-on-write efficiency. A chroot alone does not satisfy it. A virtual machine snapshot may satisfy much of it, but would need an independent demonstration of copy-on-write behavior, command interposition, and local-first operation. The hypothetical CLI also requires that the workspace be created and discarded around each command or action, not merely that a developer can start a disposable container.

Requirement (b) is the load-bearing novelty claim. It is not enough to log argv, cwd, environment, output, exit status, and elapsed time. The requirement also specifies a local, tamper-evident, hash-chained receipt and before/after file hashes. The exact chain structure—whether it is a Merkle chain, signed append-only log, salted hash chain, or something else—is not stated, so novelty cannot rest on the word “hash chain” alone. The novelty claim must instead identify the exact receipt record, the hash linkage rule, the binding between policy decision and execution result, and the verification procedure.

Requirement (c) is the semantic contract. “I fixed the bug” is not a test result. A credible verifier must parse or classify the claim, find candidate receipts, bind the claim to a command such as a test runner or build command, execute an evidence predicate against the receipt, and return one of three explicit outcomes. PASS means the specified evidence exists and satisfies the predicate. FAIL means the evidence exists and refutes the claim or fails the predicate. UNVERIFIED means there is no admissible receipt, the command did not run, the relevant output is missing, or the claim is too vague to bind. A system that returns FAIL only because an agent did not mention a test result is not verifying an action; it is applying a crude heuristic.

Requirement (d) is not equivalent to backup restore. Undo must return the workspace to a previously valid state after an arbitrary command has altered tracked files. Replay must rerun the same or equivalent command under the same recorded policy and compare the result. Neither is trivial: a backup tool may restore files while leaving processes, sockets, credentials, device state, package databases, or mounted volumes inconsistent.

Requirement (e) requires a local decision point that denies by default. An outbound HTTP allowlist, protected-path controls, and command allow/deny lists are explicit. Observability dashboards, post-hoc SIEM alerts, and rules that merely generate warnings are insufficient because they do not prevent the action.

**The review should assume documented absence is evidence of non-coverage, not cryptographic proof of impossibility.** A tool’s documentation may omit a feature, the feature may be available through an undocumented integration, or the feature may exist in a hosted commercial product not visible in the retrieved public material. The report therefore states where it did not find support and avoids saying that a tool is mathematically incapable of performing a function. The strongest conclusion the evidence can support is that no retrieved primary source demonstrates the complete five-part integration as one local-first tool.

## 2. Agent observability sees the workflow but cannot establish what physically happened

**Observability platforms are excellent for asking what an agent tried to do; they are structurally weak at proving what its shell command changed on a workstation.** They generally consume events emitted by application code. Unless the agent framework also reports complete execution metadata, the platform cannot create an authoritative receipt. Even a detailed trace remains one level removed from kernel-enforced containment and filesystem state.

| System | Documented core capability | Covers (a)–(e)? | Not demonstrated |
|---|---|---|---|
| OpenTelemetry | Vendor-neutral specification and ecosystem for generating, collecting, and exporting telemetry [1] | None directly | Command interposition, shell sandboxing, filesystem diff, local receipt chain, claim verification, policy enforcement |
| Langfuse | Traces every LLM call and relevant application logic; supports full inputs/outputs, scores, evaluations, datasets, experiments, and agent graphs [2] | Observability only | Shell execution, isolation, filesystem snapshots, receipt chain |
| AgentOps | Records each program execution as a session and displays LLM calls, action events, tool calls, and errors in a waterfall [3] | Partial trace observability | Local command interception, sandbox, filesystem hashes, hash-chained receipt, policy enforcement |
| Braintrust | Captures and analyzes agent traces, compares prompts and models, surfaces recurring problems, and supports evaluation [4] | Partial trace observability and evaluation | Shell execution, rollback, receipt chain, local command policy |
| Weave | Tracks, evaluates, and improves agents and LLM applications; traces calls and arbitrary functions and supports LLM judges and custom scorers [5] | Partial trace observability and evaluation | Sandboxed command execution, filesystem rollback, hash-chained receipt |
| Phoenix | Built on OpenTelemetry and OpenInference; captures model calls, retrieval, tool use, custom logic, and evaluations [6] | Partial trace observability and evaluation | Execution isolation, filesystem rollback, receipt chain, command policy |

**Langfuse demonstrates that tracing is necessary but insufficient.** It captures LLM calls and related logic, supports full input and output in its FULL ingestion mode, enables manual or managed LLM-as-a-judge evaluations, and can represent agents as graphs. [2] A tool could record a Langfuse trace after executing an agent command and still learn nothing trustworthy about filesystem changes. Conversely, a hash-chained local receipt can prove that `pytest` returned exit code 0 without being a full LLM-application observability platform. The two systems answer different questions: Langfuse asks how the agent behaved; the hypothetical CLI must prove what an executed action did to the local environment.

**AgentOps, Braintrust, Weave, and Phoenix add evaluation machinery, not a control plane.** AgentOps records sessions and organizes LLM calls, tool calls, and errors over time. [3] Braintrust analyzes production traces and suggests improvements. [4] Weave traces arbitrary instrumented functions and evaluates agent or application responses. [5] Phoenix scores traces and spans with LLM evaluators, code checks, or human labels. [6] These are legitimate components for triage and quality analysis. None is documented in the retrieved material as deciding whether `curl` may execute, creating a COW workspace, recording pre/post file hashes, or restoring state after a failed edit.

**Evaluation must not be mistaken for verification.** A judge may assess whether a generated answer is plausible. It does not prove that a command was executed, that the network was blocked, that the policy allowed the call, or that the exit code and file hashes were captured correctly. That distinction is critical for requirement (c). A credible verifier should treat LLM judgment as an evidence source for ambiguous prose, not as the source of truth for command execution. The authoritative record must come from the local interposition and capture layer.

## 3. Editor checkpoints prove reversible editing exists, not verifiable command execution

**Cursor-like and Cline-like checkpoints are the closest commercial analogy for undo, but they solve a narrower version of the problem.** Their evident value is restoring the state of an editing session. They do not, in the retrieved documentation, show that they capture arbitrary command metadata or cryptographically bind a command to its before/after filesystem state.

The fetched Cline documentation emphasizes explicit approval for actions, terminal and headless use, creation or modification of files, command execution, browsing, tool use, and enterprise access controls. [7] This confirms that an AI coding agent can operate in a workflow requiring approval. It does not show a local receipt format containing argv, cwd, env allowlist, stdout/stderr, exit code, file hashes, and wall time. The retrieved page also does not document a default-deny command and network policy engine or hash chaining.

The requested Cursor documentation URLs were not retrievable in this research pass, so the report does not claim to have proven what Cursor does or does not record. It can nevertheless make the narrower evidentiary point: public descriptions of editor checkpoints establish that an editing product can restore prior state, not that it satisfies (b) or (e). Without a receipt schema, policy-decision record, and capture-before-execution architecture, the checkpoint is not a verifier.

**Restore is not equivalent to reversible execution.** Git stash explicitly saves the working directory and index, reverts the working tree to HEAD, stores stash entries as commit objects, and supports apply, pop, drop, list, and show. [8] This gives a strong, well-understood reversal primitive for tracked content. It does not capture arbitrary untracked files, process state, network activity, command arguments, stdout/stderr, exit codes, or a hash chain. A stash entry may also be lost or pruned like other Git objects; its internal structure should not be represented as a tamper-evident ledger.

A checkpoint can be undone; an auditable action must also be provable. The hypothetical CLI therefore needs both a state snapshot and a separate receipt chain. If it records only the filesystem delta, it can undo but cannot necessarily prove what caused the delta. If it records only a command trace, it can explain but cannot undo.

## 4. Codex and Claude Code establish command containment, not end-to-end receipts

**Existing coding-agent sandboxes are the strongest prior art for intercepting and constraining commands, but their retrieved documentation does not establish the full receipt.** A fair novelty analysis should concede that the individual security mechanisms are mature. It should not concede that their product-level behavior is identical to the specified system.

The requested Codex and Claude Code source pages were not retrievable in this research pass. Published public material about Codex describes a sandbox and local approval controls, while Claude Code has documented permission and sandbox-related controls. These facts support the argument that the security primitives are not novel. They do not establish that either product emits a local hash-chained receipt with before/after file hashes, verifies natural-language claims against that receipt, and provides both undo and replay.

The correct prior-art framing is therefore:

- Codex-like sandboxing is prior art for (a) and partial (e), specifically command execution and local control.
- Claude Code-like permission controls are prior art for parts of (e), especially approval and tool governance.
- Neither retrieved source shows (b) as specified, (c) as specified, or integrated (d).

**A default-deny shell policy is also not new.** Linux Landlock permanently restricts a thread and its future children through composed filesystem rulesets; once set, constraints can only become stricter. [9] Bubblewrap, nsjail, Firejail, and sandbox-exec offer additional mechanisms such as user and mount namespaces, chroot or pivot_root, network namespaces, seccomp, capability dropping, and allow/deny filesystem paths. These are mature building blocks, not the hypothetical tool’s entire architecture.

Landlock’s documentation also exposes an important security lesson: it enforces restrictions but does not create an audit trail. [9] A sandbox that blocks access without recording the decision leaves an operator unable to answer which policy blocked an action, which receipt covers it, or whether the verifier is examining the same policy version. The hypothetical system should therefore record the policy version and decision inside the receipt and make that record part of the verification result.

## 5. Backup tools can restore state, but they do not establish an action’s provenance

**Restic and Borg are powerful counterexamples to the claim that reversible local state is new, but neither is a shell audit system.** They demonstrate integrity, snapshots, restore, and optional encryption. They do not mediate command execution or create a structured receipt linking a command to its effects.

Restic documents point-in-time snapshots and restoration to a selected directory, with `--overwrite` and `--delete` controlling how the target is reconciled with snapshot contents. [10] This directly supports undo. It does not, in the retrieved documentation, capture the command that made the change, its output, its exit code, its environment, or the policy decision that permitted it. Calling restic before and after every agent command would produce snapshots, but not a meaningful action receipt.

| Tool | Documented capability | Addresses | Does not address |
|---|---|---|---|
| git stash | Saves working-tree and index state; supports apply, pop, and drop [8] | Reversible working state for tracked Git content | Arbitrary shell commands, untracked files, receipt chain, sandbox policy |
| restic | Point-in-time snapshots and configurable restoration [10] | Replay/restore and state history | Command interception, output/exit capture, policy enforcement, claim verification |
| Borg | Archive snapshots, deduplication, integrity, encryption, mount/extract | Restore and historical state | Command execution capture, hash-chained action receipts, local policy enforcement |

**The correct design implication is composition, not replacement.** A COW filesystem or backup repository should provide cheap snapshots and atomic restore. An interposition layer should decide whether the command may run. A capture layer should record pre/post hashes and command metadata. A verifier should evaluate the resulting receipt. Treating the backup tool as the whole system would be an architectural category error: it can be a storage backend, but it cannot alone decide whether `rm -rf` or `curl` is permitted.

## 6. Content-addressed execution records prove outputs, not human work claims

**Build systems and provenance frameworks show that inputs, commands, and outputs can be bound by hashes, but they stop short of verifying an agent’s prose.** Their strength is deterministic identification. Their weakness is semantic: they record what the system was told to do, not whether that corresponds to what a human or agent meant by “the bug is fixed.”

Bazel remote execution material identifies actions by inputs, command, environment, output files and directories, and platform requirements, then relates those inputs to output digests. This provides a strong model for an execution identity. It is not, in the retrieved material, a local CLI that mediates arbitrary agent shell commands, records stdout/stderr, emits a hash-chained local audit record, restores pre-state, or decides whether a human-readable claim is true.

in-toto attestations provide a signed statement structure for statements about software artifacts. SLSA provides a provenance framework for how artifacts were built. Sigstore provides key and transparency-log infrastructure through Fulcio, Cosign, and Rekor. TUF protects software-update metadata and trust delegation. All are relevant to signing and verifying receipts, but none is documented in the retrieved material as a local shell interposition and rollback controller.

**Provenance proves a build path; it does not prove that the developer’s claim matches the receipt.** SLSA can support trust in where an artifact came from. It does not by itself determine that the agent’s sentence “I fixed the bug” corresponds to a passing test whose inputs and outputs are recorded. The hypothetical CLI still needs a semantic mapping from claim to evidence and a decision rule for UNVERIFIED.

A stronger version of the system would separate three concerns:

1. **Action identity:** the command, cwd, inputs, policy, and output digests.
2. **Receipt integrity:** hash chain, signatures, and a protected append-only store.
3. **Claim semantics:** predicates such as “exit code 0,” “all tests passed,” or “protected path unchanged.”

Without that separation, a signed build provenance could be confused with proof of a high-level work claim. The signature proves authorship or integrity under a stated trust model; it does not interpret the claim.

## 7. Integrity and rollback primitives are mature, but their security boundaries differ

**No single sandbox supplies all the enforcement required by (e), and several have materially different threat models.** Landlock is a kernel-enforced access-control API. Bubblewrap, nsjail, Firejail, and sandbox-exec are user-space sandboxing tools. None should be assumed to provide the same container boundary as a hypervisor or a hardened VM.

Landlock applies a composed, progressively restrictive ruleset to a thread and its descendants. [9] That makes it well suited to least-privilege filesystem enforcement. It does not inherently limit every network operation, provide a command allowlist, record execution metadata, or reverse changes after a command exits.

Bubblewrap can create new mount, PID, IPC, network, user, and UTS namespaces; discard capabilities; and use seccomp. It is a low-level sandbox primitive rather than a full developer CLI. Nsjail similarly supports filesystem mounts, chroot or pivot_root, namespaces, resource limits, capabilities, seccomp, and network configuration. These capabilities can satisfy important parts of (a) and (e), but they still require an external policy engine, snapshot mechanism, and receipt format.

**Hash chaining does not create trust by itself.** A local attacker who controls the process, key material, or underlying storage may rewrite both the state and the receipts. Replay protection requires a defined root of trust, measured boot or hardware protection where available, or at minimum a write-once store and a threat model that excludes a fully compromised host. A salted hash chain can detect modification after the fact, but it cannot prevent a privileged process from rewriting history unless the chain is append-only under a stronger protection boundary.

A defensible design should therefore support multiple integrity modes and disclose their assumptions:

| Integrity mode | What it can demonstrate | What it cannot demonstrate |
|---|---|---|
| Local hash chain | Later entries cannot be altered without breaking the chain | An attacker with write access did not rewrite the whole chain |
| Local signing | Receipts were signed by a key under the stated model | The signing key was not compromised |
| Hardware-backed key | Stronger protection of the signing key | A malicious command still cannot lie about observed output |
| Append-only remote witness | Independent parties saw an entry | The witness is honest and available |

The key limitation is that no chain or signature can prove that an unobserved command actually executed. Capture completeness is therefore a first-class security requirement, not a logging detail.

## 8. Capture completeness is the hard security boundary, not the receipt format

**The most credible attack against the hypothetical system is not hash-chain forgery; it is bypassing capture.** If the agent can invoke a shell outside the interposed wrapper, run a command before a snapshot is taken, or redirect output through an unmonitored channel, the receipt understates reality. A formally elegant receipt format cannot repair incomplete capture.

Possible bypasses include direct shell access, setuid binaries, preloaded libraries, symlinks that escape protected paths, TOCTOU races, background processes that survive the workspace, package managers that modify global state, and subagents or scripts that invoke tools indirectly. Network restrictions can also be bypassed if an allowed command itself performs network access or if the policy treats an outbound connection as a permitted side effect.

A secure architecture must therefore make interposition mandatory. Plausible mechanisms include `LD_PRELOAD` restrictions, ptrace or seccomp restrictions, wrapper binaries on `PATH`, shell-function controls, and denying execution of unknown interpreters. Every mechanism has exceptions and portability problems, so the trust model should state which platforms and execution paths are supported rather than claiming universal coverage.

**Capture itself must be treated as an adversarial interface.** A malicious command can flood logs, embed sensitive data in stdout, or emit an exit code and message designed to manipulate an LLM verifier. The CLI should record raw output separately from normalized predicates, redact secrets before optional remote export, and never let the command write the final receipt. Otherwise the system would let the subject of the audit attest on its own behalf.

The minimum capture contract should include:

- a monotonic local sequence number;
- the receipt’s own hash;
- the previous receipt hash;
- a policy version and decision result;
- command, arguments, cwd, and allowed environment variables;
- stdin or its hash;
- stdout/stderr, or a hash and length if raw capture is disabled;
- exit code, start and end times, and measured wall time;
- pre/post hashes for each tracked path or the filesystem root;
- resource and sandbox metadata;
- the hash of the action or run identifier.

This is a proposed specification, not evidence that the hypothetical project already implements it. The purpose is to make the novelty claim falsifiable: if a competitor or prior project does not publish a similar record with comparable linkage and coverage, it has not demonstrated the same receipt.

## 9. The real novelty is semantic verification, not another logging format

**“Verifies agent claims against receipts” is more novel than “logs agent actions.”** Natural-language claims are not structured events. They require entity resolution, intent classification, and a mapping to one or more receipts and predicates. The claimed novelty is therefore not simply that a tool records structured test results. It is that the system decides whether the available local evidence supports the exact claim made by the agent.

The verifier must handle at least four failure modes:

1. **No evidence:** The agent says tests passed, but no relevant test command receipt exists.
2. **Conflicting evidence:** The agent says the build succeeded, but the recorded command exited nonzero or required output is absent.
3. **Ambiguous evidence:** The claim is too vague to bind to a single command or file.
4. **Stale evidence:** A test passed earlier, but files changed afterward.

The system should not infer PASS from conversational confidence. It should return UNVERIFIED whenever binding, completeness, integrity, or policy checks fail. This is a stricter design choice, but it is the one that gives the receipt operational meaning.

A practical verifier should use deterministic and structured evidence whenever possible and invoke an LLM only for bounded semantic interpretation:

| Claim | Preferred evidence | Safer decision rule |
|---|---|---|
| “Tests pass” | Test runner exit code, structured report, and filesystem state | PASS only if an admissible test receipt matches the stated target and all required cases passed |
| “I ran the build” | Build command exit code, stdout/stderr, output artifacts, and receipt timestamp | PASS only if an admissible command receipt exists and exited 0; UNVERIFIED if the claim cannot be bound to one command |
| “I fixed the bug” | Issue-specific test or reproduction command, code delta, and exit status | UNVERIFIED unless a test or reproduction predicate is bound and satisfied; never infer from prose |
| “No secrets were exfiltrated” | Network policy decision, allowed domains, and traffic evidence | UNVERIFIED or FAIL depending on the policy and evidence model; cannot be proven merely because the agent says so |

**The semantic layer should be configurable because claim meaning is context-dependent.** In one project, “tests pass” may mean a project-wide suite. In another, it may mean one regression test. A rigid parser that assumes a universal meaning will produce false positives and false negatives. The verifier should support project-specific claim grammars, allowlists of admissible commands, structured test-result ingestion, and a policy that controls whether the LLM may assist in binding a claim.

## 10. Undo and replay are distinct guarantees and require different evidence

**Undo needs pre-state; replay needs a re-executable policy and environment.** A backup can supply the former without supplying the latter. A build cache can rerun an action without safely restoring the workspace. The hypothetical CLI needs both, and it should distinguish them in its receipt.

Restoring a restic snapshot demonstrates that historical state can be recovered. [10] Applying a Git stash demonstrates that local edits can be reverted. [8] Replay, by contrast, requires the command, cwd, allowed env, filesystem snapshot, sandbox configuration, and resource policy to be reproducible enough that rerunning produces comparable evidence. Replay cannot promise bit-identical output when commands read clocks, network state, random sources, or mutable external systems. It can promise that the same controlled action was re-executed and compared.

The system should define three separate operations:

- `undo`: restore the pre-action state.
- `rerun`: execute the recorded action again.
- `replay`: rerun and compare exit code, relevant output, and selected filesystem digests.

`replay` is not a guarantee of repeatability. It is a controlled comparison. If a test reads an external service, the comparison may fail for reasons unrelated to the agent’s change. The report should disclose this limitation and permit policy to require network isolation during reproducible replay.

**Filesystem diff is itself a policy and privacy decision.** Hashing every file may be expensive, while hashing only the cwd can miss state altered by a global package manager. The system should support configurable scope: git-tracked files, project root, allowed mounts, or a full filesystem hash. It should also support raw-output minimization where verbose logs contain secrets. The default must not silently reduce receipt completeness below what the verifier needs to make its decision.

## 11. The strongest “this already exists” arguments do not survive the full specification

**The most credible counterargument is that the hypothetical tool is just Bubblewrap plus restic plus an audit log.** This is the strongest recombination argument because it identifies real mechanisms for each requirement. It fails on integration semantics. The bundle does not automatically capture argv, exit code, stdout/stderr, env allowlist, before/after hashes, and policy decision as one receipt. It does not deterministically map a claim to those records, and it does not guarantee atomic capture and restoration.

A fair response is to concede that the tool’s architecture could be built from these parts. The novelty is then not the atoms but their binding: the policy decision and pre-snapshot occur before execution; command output and filesystem diff are captured during execution; the receipt is sealed after execution; and the same record is used for both proof and undo. If the project does not demonstrate that ordering and atomicity, it is vulnerable to the recombination objection.

**“OpenTelemetry already records everything” is not supported by the specified requirement.** OpenTelemetry standardizes telemetry semantics and export, not filesystem containment or rollback. A project could define a semantic convention for agent shell receipts, but the retrieved specification material does not establish that such a convention contains the required fields or enforces their capture. OpenTelemetry is therefore an export format candidate, not a prior-art substitute for the system. [1]

**“Langfuse/AgentOps/Braintrust/Weave/Phoenix already score agents” is true but narrow.** They can score traces and outputs, but they do not establish the physical truth of local execution. [2][3][4][5][6] The objection would be stronger if the hypothetical verifier used only LLM judging. The specification avoids that trap by requiring command metadata, output, exit status, filesystem diff, and policy evidence.

**“Git already gives reversible state and provenance” addresses only a subset.** Git stash reverses tracked working and index state and has a well-defined history mechanism, but it does not mediate command execution or enforce default-deny policies. [8] Git alone cannot show that an agent’s command was permitted, what its output was, or whether a protected path was touched.

**“in-toto/SLSA/Sigstore already provide receipts” addresses integrity, not capture or claim semantics.** These systems can sign and verify statements about artifacts or builds. They do not, in the retrieved documentation, capture arbitrary shell execution, define the required action record, or decide whether a sentence such as “I fixed the bug” is true.

**“A SIEM already does audit” misses the prevention and state guarantees.** A SIEM can receive and analyze logs, but it normally observes after the fact and does not itself create a COW sandbox or restore workspace state. It may be a downstream consumer of receipts, not the local enforcement point.

**“Tape/record-replay tools already replay execution” covers a different surface.** Tools in this category commonly record browser DOM events, user input, or application events and replay them for debugging or UI testing. They do not create least-privilege shell sandboxes or filesystem rollback systems. They may inspire the replay interface, but they are not counterexamples to (a), (e), or the receipt architecture.

**“Pytest already proves tests pass” is incomplete without execution evidence.** Pytest can produce machine-readable reports and exit nonzero on failure. The report must still be bound to the exact command, cwd, environment, output, and filesystem state, and the agent must not be trusted to relay its contents honestly. The verifier should read the test report directly from the receipt, not from the agent’s prose.

## 12. Prior art divides the specification, but no source closes the claim-to-evidence loop

**The evidence supports a capability map, not a claim that every possible counterexample has been found.** The table separates directly documented capabilities from the specified requirements. It does not prove that a hidden tool, unreleased commercial feature, or local fork does not exist.

| Category and project | Primary evidence and what it does | (a) run in isolated reversible COW workspace | (b) tamper-evident local receipt with full command metadata and file hashes | (c) verify natural-language claim against receipts | (d) undo or replay | (e) default-deny local policy |
|---|---|---:|---:|---:|---:|---:|
| OpenTelemetry [1] | Telemetry specification and ecosystem | No | No | No | No | No |
| Langfuse [2] | LLM and agent tracing, scores, evaluations, datasets | No | No | Partial evaluation, not execution verification | No | No |
| AgentOps [3] | Session replay and tool/action event recording | No | No | No | No | No |
| Braintrust [4] | Agent trace observability and improvement | No | No | Partial output evaluation | No | No |
| Weave [5] | Agent tracing, evaluation, LLM judges, custom scorers | No | No | Partial output evaluation | No | No |
| Phoenix [6] | OpenTelemetry/OpenInference tracing and trace scoring | No | No | Partial output evaluation | No | No |
| Cline [7] | AI coding agent with explicit action approval and tool use | Partial command execution | Not demonstrated | No | Not demonstrated | Partial approval workflow |
| Codex CLI public documentation | Sandboxed coding-agent command execution | Strong partial | Not demonstrated | Not demonstrated | Not demonstrated | Partial sandbox/permissions |
| Claude Code public documentation | Permission and sandbox settings | Strong partial | Not demonstrated | Not demonstrated | Not demonstrated | Partial permissions/sandbox |
| git stash [8] | Reversible working-tree and index state | No | No | No | Partial undo | No |
| restic [10] | Point-in-time snapshot restoration | No | No | No | Strong partial restore | No |
| Borg | Encrypted, deduplicated snapshot archives | No | No | No | Strong partial restore | No |
| Bubblewrap | Low-level user-space sandbox | Strong partial | No | No | No | Partial enforcement primitives |
| Firejail | Sandbox profiles and restrictions | Strong partial | No | No | No | Partial enforcement primitives |
| Landlock [9] | Kernel filesystem access-control API | Partial enforcement | No | No | No | Partial least privilege |
| sandbox-exec | macOS sandbox-profile execution | Strong partial | No | No | No | Partial enforcement |
| nsjail | Namespace, chroot/pivot_root, filesystem, network, and resource sandbox | Strong partial | No | No | No | Partial enforcement |
| Nix | Content-addressed store and environment management | Partial reproducibility | No | No | Partial generation rollback | No |
| Bazel remote execution | Content-addressed action inputs, command, environment, and output digests | No | Partial action result | No | Partial action cache | No |
| in-toto | Signed software attestation statements | No | No | No | No | No |
| SLSA | Build provenance framework | No | No | No | No | No |
| Sigstore | Signing, verification, and transparency-log infrastructure | No | Partial signing/transparency | No | No | No |
| TUF | Secure software-update metadata and trust delegation | No | No | No | No | No |
| reprotest | Reproducible-build variation testing | No | No | No | Partial variation comparison | No |
| pytest | Test runner and structured result reporting | No | No | Partial if report is read directly | Partial test rerun | No |
| Record/replay tools | Event or UI replay | No | No | No | Partial replay | No |
| OpenSSF Scorecard | Supply-chain risk checks | No | No | No | No | No |
| SIEM/audit logs | Centralized collection and analysis of audit events | No | Partial immutable-log features | No | No | No |

The map exposes the actual design gap. Multiple tools support execution containment. Multiple tools support snapshots. Several standards support signing and verification. Agent platforms support evaluation. None of the retrieved sources shows those capabilities implemented as one local action record that drives both proof and rollback.

## 13. The core novelty is enforceable claim semantics, not the individual components

**The genuine invention is an enforceable claim-to-evidence protocol, not another observability dashboard.** The protocol must define when a receipt begins, what must be captured before execution, which policy decision is authoritative, what output and filesystem state must be sealed, how the chain is linked, and what makes a claim admissible.

Four engineering artifacts would make the novelty concrete:

1. **A formal receipt grammar** covering the specified fields and their hash-link rule.
2. **A policy decision record** that captures the decision before and after enforcement.
3. **A claim-binding language** mapping natural-language utterances to admissible receipts and predicates.
4. **A verification algorithm** that returns PASS, FAIL, or UNVERIFIED with reasons.

Without these artifacts, the phrase “verifies an agent’s claims” is too vague to be examined for novelty. A conventional logger could claim to verify a claim if it merely checks that the claim appears in a record.

**The recombination parts are substantial and should be stated without embarrassment.** Bubblewrap, nsjail, Landlock, Firejail, and sandbox-exec provide sandboxing. Restic, Borg, Git, and COW filesystems provide rollback. OpenTelemetry-compatible tracing and agent observability platforms provide reporting and analysis. in-toto, SLSA, Sigstore, and TUF provide attestation and integrity models. Pytest and record/replay tools provide test evidence and replay concepts. The credible novelty story is not “no one has built any of these pieces.” It is that a coherent local control plane joins them while preserving a simple developer CLI experience.

**The weakest version of the claim is incrementally novel; the strongest version is substantially novel.** If the project is merely a wrapper that calls Bubblewrap, records stdout, and appends to a JSON log, a skeptical examiner should reject broad novelty. If it guarantees atomic capture, enforces a default-deny policy before execution, records before/after filesystem state, binds prose claims to structured predicates, supports restore and replay from one record, and provides a verifiable chain under a stated trust model, the integration becomes substantially more than a wrapper.

## 14. Credibility depends on adversarial guarantees, portability disclosures, and testable predicates

**The CLI should be judged by adversarial completeness, not feature count.** A public proof-of-concept must demonstrate what happens when a command is denied, when a protected path is touched, when output is missing, when a snapshot fails, and when an agent makes a claim with no matching receipt. It must also show whether the receipt survives those failure paths and whether a failed action can still be undone safely.

The implementation should define and test the following threat cases:

- The agent invokes an interpreter directly instead of the wrapped shell.
- A command modifies files after the post-execution hash pass.
- A setuid binary escalates privilege inside the sandbox.
- The host clock is changed.
- A signing key is stolen.
- The local receipt store is deleted or rolled back.
- A command produces huge output and attempts a log-flooding denial-of-service attack.
- A background process continues after the wrapper exits.
- Symlinks or hard links escape the intended workspace.
- Network access occurs through an allowed helper or proxy.
- Two actions race to modify the same state.

If the design cannot address these cases, the correct verdict is not “the tool makes actions auditable.” It is “the tool makes some actions auditable under favorable conditions.”

**Portability is a real novelty risk.** Landlock is Linux-specific. sandbox-exec is macOS-specific and has been deprecated in some contexts. Bubblewrap, nsjail, and Firejail have different kernel and distribution requirements. A CLI that works only on one Linux configuration can still be novel, but it must say so. A claim of universal local enforcement without per-platform threat models is not credible.

**The claim verifier needs precision, not another LLM chatbot.** Natural-language interpretation may help match “all tests” to a project’s test target, but the final PASS or FAIL must rest on deterministic checks: exit code, structured test results, file hashes, policy decision, and receipt integrity. The system should preserve raw evidence, support explanation and audit, and return UNVERIFIED rather than guessing.

The strongest novelty claim is therefore a disciplined one: the tool changes the locus of trust from the agent’s narrative to a local, policy-bound, state-aware execution record. It does not prove that an agent is honest. It proves which commands were permitted, what they emitted, how they changed the workspace, and whether those facts support the stated claim.

## 15. The exact combination is not shown by prior art; the defensible claim is a verifiable control plane

**No retrieved source demonstrates the exact combination as a single local-first developer CLI.** The evidence shows mature components across the five requirements, but not one project that integrates them with the specified receipt schema and claim-to-evidence verification loop. The most plausible explanation is that the system is a genuine integration invention built from established primitives, not that it is five independent inventions.

The strongest “this already exists” arguments should be answered as follows:

- **“It is just Bubblewrap plus restic plus a log.”** Rebut partially: the wrapper must capture, link, enforce, and verify atomically. Concede that the individual mechanisms are not new.
- **“Langfuse and similar platforms already verify agents.”** Rebut: they observe and evaluate, but do not mediate shell execution or establish local filesystem effects.
- **“Git already provides undo.”** Rebut: git stash restores tracked working and index state, not arbitrary shell actions or their audit records. [8]
- **“SLSA and Sigstore already provide receipts.”** Rebut: they provide provenance and integrity infrastructure, not a local command interposition and claim-resolution system.
- **“A backup tool already supports rollback.”** Rebut: restoration is not evidence capture, policy enforcement, or claim verification. [10]

The honest limits of this review are equally important. Several product documentation pages could not be retrieved, including the specific Codex, Claude Code, and Cursor pages. Documentation can lag implementation, vendor pages may require authentication, and an internal or commercial tool may exist outside the public material reviewed here. The report also did not inspect every release branch, plugin, or third-party extension. It therefore establishes that the complete integration is not demonstrated in the reviewed primary sources, not that it is mathematically impossible or that no unindexed project exists.

The final novelty question is empirical. Publish the receipt grammar, threat model, policy DSL, claim-binding rules, and verification algorithm. Compare the system against Bubblewrap, Landlock, restic or Borg, an observability backend, and a structured test reporter used separately. If the project still provides atomic pre-execution enforcement, a complete state-aware receipt, claim verification, and restore or replay from one record, its novelty is credible. If it merely connects those tools after the fact, it is useful engineering but a much weaker invention.

## Data sources

[1] https://opentelemetry.io/docs/specs/otel/
> “The official project name is ‘OpenTelemetry’ (with no space between ‘Open’ and ‘Telemetry’).”

[2] https://langfuse.com/docs
> “Traces allow you to track every LLM call and other relevant logic in your app.”

[3] https://docs.agentops.ai/
> “Each execution of your program is recorded as a session and the above data is automatically recorded for you.”

[4] https://braintrust.dev/docs
> “Braintrust is the active observability platform for instrumenting, understanding, and improving agents.”

[5] https://docs.wandb.ai/guides/weave
> “W&B Weave is an observability and evaluation platform that helps you track, evaluate, and improve your agents and LLM applications.”

[6] https://docs.arize.com/phoenix/
> “Phoenix is built on top of OpenTelemetry and is powered by OpenInference instrumentation.”

[7] https://docs.cline.bot/
> “Every action requires your explicit approval. You’re always in control.”

[8] https://git-scm.com/docs/git-stash
> “Use git stash when you want to record the current state of the working directory and the index.”

[9] https://www.man7.org/linux/man-pages/man2/landlock_restrict_self.2.html
> “Once a Landlock ruleset is populated with the desired rules, the landlock_restrict_self() system call enforces this ruleset on the calling thread.”

[10] https://restic.readthedocs.io/en/stable/050_restore.html
> “Restoring a snapshot is as easy as it sounds, just use the following command to restore the contents of the latest snapshot.”

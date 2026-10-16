// macOS Codex Desktop approval accessibility probe.
// Read-only diagnostic: no clicks, screenshots, persistence, hooks, or DingTalk requests.
// The matching/tracker core compiles on Linux for self-tests; AppKit scanning runs only on macOS.

import Foundation
#if canImport(AppKit) && canImport(ApplicationServices)
import AppKit
import ApplicationServices
#endif

struct ApprovalButton {
    let label: String
    let x: Double
    let y: Double
    let enabled: Bool
}

struct ApprovalWindow {
    let id: String
    let buttons: [ApprovalButton]
}

struct ApprovalMatch {
    let id: String
    let window: String
}

func buttonKind(_ label: String) -> Int {
    let cleaned = label.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    let negative = ["deny", "reject", "cancel", "don't allow", "do not allow", "skip", "not now",
                    "拒绝", "取消", "不允许", "不批准", "跳过", "暂不", "否，", "否"]
    let positive = ["allow", "always allow", "approve", "confirm", "run", "proceed", "continue",
                    "yes", "accept", "trust", "允许", "始终允许", "批准", "同意", "确认执行", "继续执行", "运行", "授权"]
    if negative.contains(where: { cleaned == $0 || cleaned.hasPrefix($0 + " ") || cleaned.hasPrefix($0 + "（") }) { return -1 }
    if positive.contains(where: { cleaned == $0 || cleaned.hasPrefix($0 + " ") || cleaned.hasPrefix($0 + "（") }) { return 1 }
    return 0
}

// Require two ENABLED, nearby, opposite-action buttons within the SAME visible window.
// A button's presence alone is not enough to classify a pending approval.
func findApprovals(_ windows: [ApprovalWindow]) -> [ApprovalMatch] {
    var matches: [ApprovalMatch] = []
    for window in windows {
        let positives = window.buttons.filter { $0.enabled && buttonKind($0.label) == 1 }
        let negatives = window.buttons.filter { $0.enabled && buttonKind($0.label) == -1 }
        var keys: Set<String> = []
        for positive in positives {
            let nearby = negatives.filter {
                abs($0.y - positive.y) <= 160 && abs($0.x - positive.x) <= 750
            }
            guard let negative = nearby.min(by: {
                hypot($0.x - positive.x, $0.y - positive.y) < hypot($1.x - positive.x, $1.y - positive.y)
            }) else { continue }
            // Windows/controls do not always expose stable IDs. Use an approximate row location.
            // A removed approval is forgotten, so the next approval at the same position is new.
            let row = Int((min(positive.y, negative.y) / 120.0).rounded())
            let key = "\(window.id):row-\(row)"
            if keys.insert(key).inserted {
                matches.append(ApprovalMatch(id: key, window: window.id))
            }
        }
    }
    return matches
}

struct PendingApproval {
    let startedAt: TimeInterval
    var notified: Bool = false
}

final class ApprovalTracker {
    private var pending: [String: PendingApproval] = [:]
    let delay: TimeInterval

    init(delay: TimeInterval = 5.0) { self.delay = delay }

    func update(matches: [ApprovalMatch], at now: TimeInterval) -> [[String: Any]] {
        var events: [[String: Any]] = []
        let ids = Set(matches.map(\.id))
        for key in pending.keys.sorted() where !ids.contains(key) {
            let item = pending.removeValue(forKey: key)!
            events.append(["event": "approval_cleared", "approval_id": key,
                           "elapsed_s": round((now - item.startedAt) * 10) / 10])
        }
        for match in matches.sorted(by: { $0.id < $1.id }) {
            if pending[match.id] == nil {
                pending[match.id] = PendingApproval(startedAt: now)
                events.append(["event": "approval_detected", "approval_id": match.id])
            } else if var item = pending[match.id], !item.notified, now - item.startedAt >= delay {
                item.notified = true
                pending[match.id] = item
                events.append(["event": "approval_pending_5s", "approval_id": match.id,
                               "elapsed_s": round((now - item.startedAt) * 10) / 10])
            }
        }
        return events
    }

    func reset() { pending.removeAll() }
}

func emit(_ body: [String: Any]) {
    var event = body
    event["timestamp"] = ISO8601DateFormatter().string(from: Date())
    if let json = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys]) {
        FileHandle.standardOutput.write(json)
        FileHandle.standardOutput.write(Data([10]))
    }
}

func runSelfTest() -> Int32 {
    let allow = ApprovalButton(label: "Allow once", x: 400, y: 300, enabled: true)
    let deny = ApprovalButton(label: "Deny", x: 520, y: 300, enabled: true)
    let no = ApprovalButton(label: "Cancel", x: 520, y: 300, enabled: true)
    let notApproval = ApprovalButton(label: "Open", x: 400, y: 300, enabled: true)
    func test(_ condition: Bool, _ message: String) -> Bool {
        if !condition { fputs("FAIL: \(message)\n", stderr) }
        return condition
    }
    var ok = true
    let fixture = ApprovalWindow(id: "codex:win-1", buttons: [allow, deny])
    ok = test(findApprovals([fixture]).count == 1, "detect actionable pair") && ok
    ok = test(findApprovals([ApprovalWindow(id: "w", buttons: [notApproval, no])]).isEmpty,
              "ignore normal cancel dialogs") && ok
    ok = test(findApprovals([ApprovalWindow(id: "w", buttons: [allow, ApprovalButton(label: "Deny", x: 520, y: 300, enabled: false)])]).isEmpty,
              "ignore disabled controls") && ok
    ok = test(findApprovals([ApprovalWindow(id: "w", buttons: [allow]), ApprovalWindow(id: "w2", buttons: [deny])]).isEmpty,
              "never combine buttons from different windows") && ok
    let tracker = ApprovalTracker(delay: 5)
    let first = findApprovals([fixture])
    ok = test(tracker.update(matches: first, at: 100).map { $0["event"] as? String } == ["approval_detected"], "start") && ok
    ok = test(tracker.update(matches: first, at: 104.9).isEmpty, "no early notification") && ok
    ok = test(tracker.update(matches: first, at: 105).map { $0["event"] as? String } == ["approval_pending_5s"], "pending at 5s") && ok
    ok = test(tracker.update(matches: first, at: 120).isEmpty, "no duplicate") && ok
    ok = test(tracker.update(matches: [], at: 121).map { $0["event"] as? String } == ["approval_cleared"], "approval resolves") && ok
    ok = test(tracker.update(matches: first, at: 125).map { $0["event"] as? String } == ["approval_detected"], "new approval at same location") && ok
    if ok { print("PASS: approval matching, 5s timing, clear, and dedup") }
    return ok ? 0 : 1
}

#if canImport(AppKit) && canImport(ApplicationServices)
private func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var result: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, name as CFString, &result) == .success ? result : nil
}

private func axText(_ element: AXUIElement, _ keys: [String]) -> String {
    for key in keys {
        if let text = attribute(element, key) as? String, !text.isEmpty { return text }
    }
    return ""
}

private func children(_ element: AXUIElement) -> [AXUIElement] {
    // In Electron/Chromium trees AXVisibleChildren may be unavailable.
    if let visible = attribute(element, "AXVisibleChildren") as? [AXUIElement], !visible.isEmpty {
        return visible
    }
    return attribute(element, "AXChildren") as? [AXUIElement] ?? []
}

private func location(_ element: AXUIElement) -> (Double, Double)? {
    guard let raw = attribute(element, "AXPosition"), CFGetTypeID(raw) == AXValueGetTypeID() else { return nil }
    var point = CGPoint.zero
    guard AXValueGetValue(raw as! AXValue, .cgPoint, &point) else { return nil }
    return (Double(point.x), Double(point.y))
}

private func isEnabled(_ element: AXUIElement) -> Bool {
    return (attribute(element, "AXEnabled") as? Bool) ?? true
}

struct UIScan {
    let status: String
    let windows: [ApprovalWindow]
    let buttonLabels: [String]
}

func scanCodex() -> UIScan {
    guard AXIsProcessTrusted() else { return UIScan(status: "accessibility_permission_required", windows: [], buttonLabels: []) }
    let apps = NSWorkspace.shared.runningApplications.filter { $0.bundleIdentifier == "com.openai.codex" && !$0.isTerminated }
    guard !apps.isEmpty else { return UIScan(status: "codex_not_running", windows: [], buttonLabels: []) }
    var allWindows: [ApprovalWindow] = []
    var allLabels: [String] = []
    var accessibleApps = 0
    for app in apps {
        let element = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(element, 0.5)
        guard let axWindows = attribute(element, "AXWindows") as? [AXUIElement] else { continue }
        accessibleApps += 1
        for (windowIndex, window) in axWindows.enumerated() {
            if (attribute(window, "AXMinimized") as? Bool) == true { continue }
            // Do not log a window title, identifier, project name, or user content.
            let stableID = "\(app.processIdentifier):window-\(windowIndex)"
            var stack: [(AXUIElement, Int)] = [(window, 0)]
            var buttons: [ApprovalButton] = []
            var visited = 0
            while let entry = stack.popLast(), visited < 3500 {
                let (node, depth) = entry
                visited += 1
                let role = axText(node, ["AXRole"])
                if role == "AXButton" || role == "AXRadioButton" {
                    let label = axText(node, ["AXTitle", "AXDescription", "AXHelp", "AXValue"])
                    if !label.isEmpty {
                        if allLabels.count < 160 { allLabels.append(label) }
                        if let (x, y) = location(node) {
                            buttons.append(ApprovalButton(label: label, x: x, y: y, enabled: isEnabled(node)))
                        }
                    }
                }
                if depth < 35 {
                    for child in children(node).reversed() { stack.append((child, depth + 1)) }
                }
            }
            allWindows.append(ApprovalWindow(id: stableID, buttons: buttons))
        }
    }
    if accessibleApps == 0 || allWindows.isEmpty {
        return UIScan(status: "windows_not_accessible", windows: [], buttonLabels: allLabels)
    }
    return UIScan(status: "ok", windows: allWindows, buttonLabels: allLabels)
}
#endif

struct Options {
    var once = false
    var inspect = false
    var selfTest = false
    var interval = 0.5
    var delay = 5.0
}

func parseArguments(_ args: [String]) -> Options? {
    var options = Options()
    var i = 0
    while i < args.count {
        switch args[i] {
        case "--once": options.once = true
        case "--inspect": options.inspect = true; options.once = true
        case "--watch": options.once = false
        case "--self-test": options.selfTest = true
        case "--interval", "--delay":
            guard i + 1 < args.count, let value = Double(args[i + 1]), value.isFinite, value > 0 else { return nil }
            if args[i] == "--interval" { options.interval = value } else { options.delay = value }
            i += 1
        case "--help", "-h":
            print("Usage: approval_probe [--once | --inspect | --watch] [--delay 5] [--interval 0.5] [--self-test]")
            exit(0)
        default: return nil
        }
        i += 1
    }
    guard options.interval >= 0.25 && options.interval <= 10 else { return nil }
    return options
}

let options = parseArguments(Array(CommandLine.arguments.dropFirst()))
if let options {
    if options.selfTest { exit(runSelfTest()) }
    #if canImport(AppKit) && canImport(ApplicationServices)
    let tracker = ApprovalTracker(delay: options.delay)
    var previousStatus = ""
    repeat {
        let sample = scanCodex()
        let matches = sample.status == "ok" ? findApprovals(sample.windows) : []
        if sample.status != previousStatus {
            emit(["event": "scanner_status", "status": sample.status])
            previousStatus = sample.status
        }
        if sample.status == "ok" {
            if options.once { emit(["event": "snapshot", "approval_count": matches.count, "window_count": sample.windows.count]) }
            for event in tracker.update(matches: matches, at: ProcessInfo.processInfo.systemUptime) { emit(event) }
        } else {
            // Never interpret an inaccessible/minimized tree as the user having approved.
            tracker.reset()
        }
        if options.inspect {
            // Debug mode only: BUTTON labels, never chat content or command details.
            let safe = sample.buttonLabels.prefix(80).map { label -> String in
                let limited = String(label.prefix(50))
                return limited.replacingOccurrences(of: "https?://\\S+", with: "[URL]", options: .regularExpression)
            }
            emit(["event": "visible_button_labels", "labels": safe])
        }
        if !options.once { Thread.sleep(forTimeInterval: options.interval) }
    } while !options.once
    if previousStatus == "accessibility_permission_required" { exit(2) }
    #else
    emit(["event": "unsupported_platform", "reason": "macOS AppKit and Accessibility are required"])
    exit(2)
    #endif
} else {
    fputs("Invalid arguments. Use --help.\n", stderr)
    exit(2)
}
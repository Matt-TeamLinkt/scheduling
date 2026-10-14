/* @ds-bundle: {"format":4,"namespace":"TeamLinktDesignSystem_019dd0","components":[],"sourceHashes":{"ui_kits/admin/Button.jsx":"a876ee8d37c5","ui_kits/admin/Card.jsx":"4e63b422379c","ui_kits/admin/Emi.jsx":"f5f97e544836","ui_kits/admin/Field.jsx":"0ba04654502c","ui_kits/admin/PageHeader.jsx":"6e66363bca5f","ui_kits/admin/RegistrationForm.jsx":"9bed55327db0","ui_kits/admin/RosterTable.jsx":"a83916eb514d","ui_kits/admin/ScheduleGrid.jsx":"167214061fd7","ui_kits/admin/Sidebar.jsx":"f52baf24094a","ui_kits/admin/Topbar.jsx":"09277ac00f45","ui_kits/team-app/ChatList.jsx":"f41e80b91fb1","ui_kits/team-app/EventCard.jsx":"77aaa27c5881","ui_kits/team-app/Login.jsx":"77938973000a","ui_kits/team-app/RosterList.jsx":"c3c6f44cf149","ui_kits/team-app/Screen.jsx":"3c054959cfbb","ui_kits/team-app/TabBar.jsx":"91054bfb400c","ui_kits/team-app/ios-frame.jsx":"d67eb3ffe562"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.TeamLinktDesignSystem_019dd0 = window.TeamLinktDesignSystem_019dd0 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// ui_kits/admin/Button.jsx
try { (() => {
function Button({
  variant = "solid",
  size = "md",
  icon,
  children,
  onClick,
  style
}) {
  const base = {
    fontFamily: "'Be Vietnam Pro',sans-serif",
    fontWeight: 500,
    letterSpacing: "-.02em",
    border: 0,
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    transition: "background .15s ease, transform .05s ease"
  };
  const sizes = {
    sm: {
      fontSize: 14,
      lineHeight: "18px",
      padding: "8px 12px"
    },
    md: {
      fontSize: 16,
      lineHeight: "20px",
      padding: "10px 14px"
    },
    lg: {
      fontSize: 16,
      lineHeight: "20px",
      padding: "12px 16px"
    }
  };
  const variants = {
    solid: {
      background: "rgb(36,84,255)",
      color: "#fff",
      borderRadius: 10
    },
    pill: {
      background: "rgb(36,84,255)",
      color: "#fff",
      borderRadius: 100,
      padding: "12px 16px"
    },
    dark: {
      background: "rgb(28,32,36)",
      color: "#fff",
      borderRadius: 10
    },
    soft: {
      background: "rgba(1,68,255,.06)",
      color: "rgb(36,84,255)",
      borderRadius: 10
    },
    ghost: {
      background: "transparent",
      color: "rgb(28,32,36)",
      borderRadius: 10
    },
    danger: {
      background: "rgba(243,0,13,.08)",
      color: "rgb(198,42,47)",
      borderRadius: 10
    }
  };
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    style: {
      ...base,
      ...sizes[size],
      ...variants[variant],
      ...style
    }
  }, icon && /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 18
    }
  }, icon), children);
}
function IconButton({
  icon,
  onClick,
  style
}) {
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    style: {
      width: 40,
      height: 40,
      borderRadius: 10,
      border: 0,
      cursor: "pointer",
      background: "transparent",
      color: "rgba(0,37,158,.8)",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 20
    }
  }, icon));
}
window.Button = Button;
window.IconButton = IconButton;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/Button.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/Card.jsx
try { (() => {
function Card({
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid rgb(225,227,234)",
      borderRadius: 12,
      boxShadow: "0 1px 2px rgba(14,18,22,.07)",
      padding: 16,
      ...style
    }
  }, children);
}
function StatCard({
  label,
  value,
  delta,
  deltaTone = "success",
  sub
}) {
  const tones = {
    success: {
      bg: "rgba(48,164,108,.1)",
      fg: "rgb(24,121,78)"
    },
    error: {
      bg: "rgba(243,0,13,.08)",
      fg: "rgb(198,42,47)"
    },
    neutral: {
      bg: "rgb(235,235,239)",
      fg: "rgb(96,100,108)"
    }
  };
  const t = tones[deltaTone];
  return /*#__PURE__*/React.createElement(Card, {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 8,
      minWidth: 200
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(112,112,123)",
      letterSpacing: "-.02em"
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 500,
      fontSize: 32,
      lineHeight: "36px",
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, value), delta && /*#__PURE__*/React.createElement("span", {
    style: {
      alignSelf: "flex-start",
      fontSize: 12,
      padding: "4px 10px",
      borderRadius: 100,
      background: t.bg,
      color: t.fg,
      fontWeight: 500
    }
  }, delta), sub && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(112,112,123)"
    }
  }, sub));
}
function Badge({
  tone = "neutral",
  children
}) {
  const tones = {
    neutral: {
      bg: "rgb(235,235,239)",
      fg: "rgb(96,100,108)"
    },
    info: {
      bg: "rgb(235,242,255)",
      fg: "rgb(36,84,255)"
    },
    success: {
      bg: "rgba(48,164,108,.1)",
      fg: "rgb(24,121,78)"
    },
    warn: {
      bg: "rgba(229,159,41,.12)",
      fg: "rgb(176,113,17)"
    },
    error: {
      bg: "rgba(243,0,13,.08)",
      fg: "rgb(198,42,47)"
    }
  };
  const t = tones[tone];
  return /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      fontWeight: 500,
      padding: "4px 10px",
      borderRadius: 100,
      background: t.bg,
      color: t.fg,
      letterSpacing: "-.02em"
    }
  }, children);
}
window.Card = Card;
window.StatCard = StatCard;
window.Badge = Badge;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/Card.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/Emi.jsx
try { (() => {
function Emi({
  open,
  onClose
}) {
  const [msgs, setMsgs] = React.useState([{
    role: "assistant",
    text: "Hi! I'm Emi. I can help draft schedules, registration forms, or messages to your members. What are we working on?"
  }]);
  const [input, setInput] = React.useState("");
  if (!open) return null;
  const send = () => {
    if (!input.trim()) return;
    const u = input;
    setMsgs(m => [...m, {
      role: "user",
      text: u
    }, {
      role: "assistant",
      text: "Got it — I'll draft that and put it in your queue. Want me to also notify the team admins?"
    }]);
    setInput("");
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: "fixed",
      right: 24,
      bottom: 24,
      width: 380,
      maxHeight: 560,
      background: "#fff",
      borderRadius: 16,
      boxShadow: "0 12px 32px rgba(14,18,22,.18)",
      border: "1px solid rgb(225,227,234)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      zIndex: 50
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "14px 16px",
      display: "flex",
      alignItems: "center",
      gap: 10,
      borderBottom: "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: 10,
      background: "rgb(235,242,255)",
      color: "rgb(36,84,255)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 20
    }
  }, "auto_awesome")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, "Emi"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(112,112,123)"
    }
  }, "AI assistant \xB7 always free")), /*#__PURE__*/React.createElement(IconButton, {
    icon: "close",
    onClick: onClose
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: "auto",
      padding: 16,
      display: "flex",
      flexDirection: "column",
      gap: 10
    }
  }, msgs.map((m, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      alignSelf: m.role === "user" ? "flex-end" : "flex-start",
      maxWidth: "85%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "10px 12px",
      borderRadius: 12,
      fontSize: 14,
      letterSpacing: "-.02em",
      lineHeight: "20px",
      background: m.role === "user" ? "rgb(36,84,255)" : "rgb(249,249,249)",
      color: m.role === "user" ? "#fff" : "rgb(32,32,32)"
    }
  }, m.text)))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 12,
      borderTop: "1px solid rgb(225,227,234)",
      display: "flex",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("input", {
    value: input,
    onChange: e => setInput(e.target.value),
    onKeyDown: e => e.key === "Enter" && send(),
    placeholder: "Ask Emi to draft something\u2026",
    style: {
      flex: 1,
      padding: "10px 12px",
      border: "1px solid rgb(209,209,214)",
      borderRadius: 10,
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontSize: 14,
      letterSpacing: "-.02em",
      outline: 0
    }
  }), /*#__PURE__*/React.createElement(Button, {
    variant: "solid",
    onClick: send,
    icon: "arrow_upward"
  })));
}
window.Emi = Emi;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/Emi.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/Field.jsx
try { (() => {
function Field({
  label,
  value,
  onChange,
  placeholder,
  help,
  error,
  type = "text"
}) {
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    style: {
      display: "block",
      fontSize: 14,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em",
      marginBottom: 6
    }
  }, label), /*#__PURE__*/React.createElement("input", {
    type: type,
    value: value,
    onChange: e => onChange && onChange(e.target.value),
    placeholder: placeholder,
    style: {
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontSize: 14,
      lineHeight: "20px",
      letterSpacing: "-.02em",
      width: "100%",
      padding: "10px 12px",
      border: `1px solid ${error ? "rgb(243,0,13)" : "rgb(209,209,214)"}`,
      borderRadius: 10,
      background: "#fff",
      color: "#000",
      boxSizing: "border-box",
      outline: 0
    }
  }), help && !error && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(112,112,123)",
      marginTop: 4
    }
  }, help), error && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(243,0,13)",
      marginTop: 4
    }
  }, error));
}
function Select({
  label,
  value,
  onChange,
  options
}) {
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    style: {
      display: "block",
      fontSize: 14,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em",
      marginBottom: 6
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement("select", {
    value: value,
    onChange: e => onChange && onChange(e.target.value),
    style: {
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontSize: 14,
      letterSpacing: "-.02em",
      width: "100%",
      padding: "10px 36px 10px 12px",
      appearance: "none",
      border: "1px solid rgb(209,209,214)",
      borderRadius: 10,
      background: "#fff",
      color: "#000",
      outline: 0
    }
  }, options.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value,
    value: o.value
  }, o.label))), /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      position: "absolute",
      right: 10,
      top: 10,
      pointerEvents: "none",
      color: "rgb(112,112,123)",
      fontSize: 20
    }
  }, "keyboard_arrow_down")));
}
window.Field = Field;
window.Select = Select;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/Field.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/PageHeader.jsx
try { (() => {
function PageHeader({
  title,
  onBack,
  actions
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "24px",
      background: "rgb(249,249,249)",
      display: "flex",
      alignItems: "center",
      gap: 16,
      borderBottom: "1px solid rgb(225,227,234)"
    }
  }, onBack && /*#__PURE__*/React.createElement(IconButton, {
    icon: "arrow_back",
    onClick: onBack
  }), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontWeight: 500,
      fontSize: 24,
      lineHeight: "28px",
      letterSpacing: "-.02em",
      color: "#000",
      flex: 1
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8
    }
  }, actions));
}
window.PageHeader = PageHeader;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/PageHeader.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/RegistrationForm.jsx
try { (() => {
function RegistrationForm() {
  return /*#__PURE__*/React.createElement(Card, {
    style: {
      maxWidth: 720,
      padding: 32
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(36,84,255)",
      fontWeight: 500,
      letterSpacing: "-.02em"
    }
  }, "Spring 2026 \xB7 Soccer"), /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: "6px 0 4px",
      fontWeight: 500,
      fontSize: 24,
      letterSpacing: "-.02em",
      color: "#000"
    }
  }, "U13 AA Player Registration"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 24px",
      fontSize: 14,
      color: "rgb(32,32,32)",
      letterSpacing: "-.02em"
    }
  }, "Tell us about your player. Payment will be collected at the end of the form."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Field, {
    label: "Player first name",
    value: "Avery"
  }), /*#__PURE__*/React.createElement(Field, {
    label: "Player last name",
    value: "Thompson"
  }), /*#__PURE__*/React.createElement(Field, {
    label: "Date of birth",
    value: "2013-04-12",
    type: "date"
  }), /*#__PURE__*/React.createElement(Select, {
    label: "Preferred position",
    value: "midfield",
    options: [{
      value: "goalie",
      label: "Goalkeeper"
    }, {
      value: "defense",
      label: "Defense"
    }, {
      value: "midfield",
      label: "Midfield"
    }, {
      value: "forward",
      label: "Forward"
    }]
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      gridColumn: "1 / -1"
    }
  }, /*#__PURE__*/React.createElement(Field, {
    label: "Parent / guardian email",
    value: "",
    placeholder: "parent@example.com",
    help: "We'll send confirmations and reminders here."
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      gridColumn: "1 / -1"
    }
  }, /*#__PURE__*/React.createElement(Field, {
    label: "Emergency contact",
    placeholder: "Name and phone number"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 24,
      padding: "16px",
      background: "rgb(249,249,249)",
      borderRadius: 10,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "rgb(112,112,123)"
    }
  }, "Registration fee"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 24,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, "$185.00")), /*#__PURE__*/React.createElement(Button, {
    variant: "pill",
    size: "lg"
  }, "Continue to payment")));
}
window.RegistrationForm = RegistrationForm;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/RegistrationForm.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/RosterTable.jsx
try { (() => {
function RosterTable({
  players
}) {
  return /*#__PURE__*/React.createElement(Card, {
    style: {
      padding: 0,
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "56px 2fr 1fr 1fr 1fr 80px",
      gap: 0,
      background: "rgb(249,249,249)",
      padding: "12px 16px",
      fontSize: 12,
      fontWeight: 500,
      color: "rgb(112,112,123)",
      letterSpacing: "-.02em",
      borderBottom: "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement("div", null, "#"), /*#__PURE__*/React.createElement("div", null, "Player"), /*#__PURE__*/React.createElement("div", null, "Position"), /*#__PURE__*/React.createElement("div", null, "Status"), /*#__PURE__*/React.createElement("div", null, "Registered"), /*#__PURE__*/React.createElement("div", null)), players.map((p, i) => /*#__PURE__*/React.createElement("div", {
    key: p.id,
    style: {
      display: "grid",
      gridTemplateColumns: "56px 2fr 1fr 1fr 1fr 80px",
      gap: 0,
      padding: "14px 16px",
      fontSize: 14,
      color: "rgb(32,32,32)",
      borderBottom: i === players.length - 1 ? "none" : "1px solid rgb(225,227,234)",
      alignItems: "center",
      letterSpacing: "-.02em"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      color: "rgb(112,112,123)"
    }
  }, p.num), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: "50%",
      background: "rgb(235,242,255)",
      color: "rgb(36,84,255)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 12,
      fontWeight: 500
    }
  }, p.initials), /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 500,
      color: "#000"
    }
  }, p.name)), /*#__PURE__*/React.createElement("div", null, p.pos), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Badge, {
    tone: p.statusTone
  }, p.status)), /*#__PURE__*/React.createElement("div", {
    style: {
      color: "rgb(112,112,123)"
    }
  }, p.registered), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "right"
    }
  }, /*#__PURE__*/React.createElement(IconButton, {
    icon: "more_vert"
  })))));
}
window.RosterTable = RosterTable;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/RosterTable.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/ScheduleGrid.jsx
try { (() => {
function ScheduleGrid({
  events
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 10
    }
  }, events.map(e => /*#__PURE__*/React.createElement(Card, {
    key: e.id,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 16,
      padding: "14px 16px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 56,
      textAlign: "center",
      padding: "6px 0",
      borderRadius: 10,
      background: "rgb(235,242,255)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 500,
      color: "rgb(36,84,255)",
      textTransform: "uppercase",
      letterSpacing: ".04em"
    }
  }, e.month), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 20,
      fontWeight: 500,
      color: "rgb(36,84,255)",
      lineHeight: "24px"
    }
  }, e.day)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, e.title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "rgb(112,112,123)",
      marginTop: 2
    }
  }, e.time, " \xB7 ", e.location)), /*#__PURE__*/React.createElement(Badge, {
    tone: e.kind === "Game" ? "info" : "neutral"
  }, e.kind), /*#__PURE__*/React.createElement(IconButton, {
    icon: "chevron_right"
  }))));
}
window.ScheduleGrid = ScheduleGrid;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/ScheduleGrid.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/Sidebar.jsx
try { (() => {
function Sidebar({
  active = "dashboard",
  onNav
}) {
  const items = [{
    id: "dashboard",
    icon: "dashboard",
    label: "Dashboard"
  }, {
    id: "registrations",
    icon: "how_to_reg",
    label: "Registrations",
    badge: "3"
  }, {
    id: "teams",
    icon: "groups",
    label: "Teams & Rosters"
  }, {
    id: "schedule",
    icon: "event",
    label: "Schedule"
  }, {
    id: "payments",
    icon: "payments",
    label: "Payments"
  }, {
    id: "comms",
    icon: "campaign",
    label: "Communications"
  }, {
    id: "website",
    icon: "language",
    label: "Website"
  }, {
    id: "reports",
    icon: "insights",
    label: "Reports"
  }, {
    id: "settings",
    icon: "settings",
    label: "Settings"
  }];
  return /*#__PURE__*/React.createElement("nav", {
    style: {
      width: 248,
      padding: "16px 12px",
      background: "#fff",
      borderRight: "1px solid rgb(225,227,234)",
      height: "100%",
      boxSizing: "border-box",
      display: "flex",
      flexDirection: "column",
      gap: 2
    }
  }, items.map(it => {
    const on = active === it.id;
    return /*#__PURE__*/React.createElement("div", {
      key: it.id,
      onClick: () => onNav && onNav(it.id),
      style: {
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        borderRadius: 10,
        color: on ? "rgb(36,84,255)" : "rgb(32,32,32)",
        background: on ? "rgba(1,68,255,.06)" : "transparent",
        fontWeight: 500,
        fontSize: 14,
        letterSpacing: "-.02em",
        cursor: "pointer",
        userSelect: "none"
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: "material-symbols-rounded",
      style: {
        fontSize: 20,
        color: on ? "rgb(36,84,255)" : "rgb(112,112,123)"
      }
    }, it.icon), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1
      }
    }, it.label), it.badge && /*#__PURE__*/React.createElement("span", {
      style: {
        background: "rgb(36,84,255)",
        color: "#fff",
        fontSize: 11,
        fontWeight: 500,
        padding: "2px 8px",
        borderRadius: 100
      }
    }, it.badge));
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("div", {
    onClick: () => onNav && onNav("emi"),
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "10px 12px",
      borderRadius: 10,
      background: "linear-gradient(90deg, rgba(36,84,255,.08), rgba(36,84,255,.02))",
      color: "rgb(36,84,255)",
      fontWeight: 500,
      fontSize: 14,
      letterSpacing: "-.02em",
      cursor: "pointer"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 20
    }
  }, "auto_awesome"), "Ask Emi"));
}
window.Sidebar = Sidebar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/Sidebar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/admin/Topbar.jsx
try { (() => {
// node-derived from /DT-11107/Mobile + /DT-11104 headers
// Top bar: 64 outer / 48 inner pill on rgb(250,250,250), 12 radius

function Topbar({
  user = "FS"
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "tl-topbar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "tl-topbar-inner"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      paddingLeft: 12
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/teamlinkt-wordmark-blue.svg",
    style: {
      height: 24
    },
    alt: "TeamLinkt"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 4,
      paddingRight: 8
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 4,
      padding: "14px 8px",
      border: 0,
      background: "transparent",
      cursor: "pointer",
      fontWeight: 500,
      fontSize: 16,
      letterSpacing: "-.02em",
      color: "rgb(19,19,22)"
    }
  }, "EN ", /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 20,
      color: "rgb(112,112,123)"
    }
  }, "keyboard_arrow_down")), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: "50%",
      background: "rgb(36,84,255)",
      color: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontWeight: 500,
      fontSize: 14,
      marginRight: 8,
      marginLeft: 4
    }
  }, user))));
}
window.Topbar = Topbar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/admin/Topbar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/ChatList.jsx
try { (() => {
function ChatList({
  chats,
  onOpen
}) {
  return /*#__PURE__*/React.createElement("div", null, chats.map((c, i) => /*#__PURE__*/React.createElement("div", {
    key: c.id,
    onClick: () => onOpen && onOpen(c.id),
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "12px 16px",
      cursor: "pointer",
      borderBottom: i === chats.length - 1 ? "none" : "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement(MAvatar, {
    initials: c.initials,
    color: c.color || "rgb(36,84,255)",
    size: 44
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "baseline",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontSize: 15,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em",
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap"
    }
  }, c.name), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "rgb(112,112,123)"
    }
  }, c.time)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      marginTop: 2
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontSize: 14,
      color: "rgb(112,112,123)",
      letterSpacing: "-.02em",
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap"
    }
  }, c.preview), c.unread && /*#__PURE__*/React.createElement("span", {
    style: {
      minWidth: 20,
      height: 20,
      padding: "0 6px",
      borderRadius: 10,
      background: "rgb(36,84,255)",
      color: "#fff",
      fontSize: 11,
      fontWeight: 500,
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, c.unread))))));
}
function ChatThread({
  messages,
  onSend
}) {
  const [input, setInput] = React.useState("");
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      height: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: "auto",
      padding: "12px 16px",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      background: "rgb(249,249,249)"
    }
  }, messages.map((m, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      alignSelf: m.me ? "flex-end" : "flex-start",
      maxWidth: "78%",
      display: "flex",
      gap: 8,
      alignItems: "flex-end"
    }
  }, !m.me && /*#__PURE__*/React.createElement(MAvatar, {
    initials: m.initials,
    size: 28,
    color: m.color || "rgb(112,112,123)"
  }), /*#__PURE__*/React.createElement("div", null, !m.me && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: "rgb(112,112,123)",
      marginLeft: 10,
      marginBottom: 2
    }
  }, m.name), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "8px 12px",
      borderRadius: 16,
      background: m.me ? "rgb(36,84,255)" : "#fff",
      color: m.me ? "#fff" : "rgb(32,32,32)",
      fontSize: 14,
      lineHeight: "20px",
      letterSpacing: "-.02em",
      border: m.me ? "none" : "1px solid rgb(225,227,234)"
    }
  }, m.text))))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8,
      padding: "10px 12px",
      background: "#fff",
      borderTop: "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      width: 36,
      height: 36,
      borderRadius: "50%",
      border: 0,
      background: "rgb(249,249,249)",
      color: "rgb(112,112,123)",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 20
    }
  }, "add")), /*#__PURE__*/React.createElement("input", {
    value: input,
    onChange: e => setInput(e.target.value),
    onKeyDown: e => {
      if (e.key === "Enter" && input.trim()) {
        onSend && onSend(input);
        setInput("");
      }
    },
    placeholder: "Message",
    style: {
      flex: 1,
      padding: "8px 14px",
      border: "1px solid rgb(225,227,234)",
      borderRadius: 18,
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontSize: 14,
      outline: 0,
      letterSpacing: "-.02em"
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      if (input.trim()) {
        onSend && onSend(input);
        setInput("");
      }
    },
    style: {
      width: 36,
      height: 36,
      borderRadius: "50%",
      border: 0,
      background: "rgb(36,84,255)",
      color: "#fff",
      cursor: "pointer",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 18
    }
  }, "arrow_upward"))));
}
window.ChatList = ChatList;
window.ChatThread = ChatThread;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/ChatList.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/EventCard.jsx
try { (() => {
// Big "next event" hero card on Home
function NextEventCard({
  event,
  onOpen
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onOpen,
    style: {
      margin: "0 16px",
      padding: 20,
      borderRadius: 16,
      background: "linear-gradient(140deg, rgb(36,84,255) 0%, rgb(0,90,255) 100%)",
      color: "#fff",
      boxShadow: "0 8px 22px rgba(36,84,255,.25)",
      cursor: "pointer",
      position: "relative",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      right: -30,
      top: -30,
      width: 160,
      height: 160,
      borderRadius: "50%",
      background: "rgba(255,255,255,.08)"
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 500,
      letterSpacing: ".06em",
      textTransform: "uppercase",
      opacity: .85
    }
  }, "Next up"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 6,
      fontSize: 22,
      fontWeight: 500,
      lineHeight: "26px",
      letterSpacing: "-.02em"
    }
  }, event.title), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 6,
      fontSize: 14,
      opacity: .9,
      letterSpacing: "-.02em"
    }
  }, event.when, " \xB7 ", event.where), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 16,
      display: "flex",
      alignItems: "center",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: "flex",
      gap: 10,
      alignItems: "center"
    }
  }, [..."AB CD EF".split(" ")].map((i, k) => /*#__PURE__*/React.createElement(MAvatar, {
    key: k,
    initials: i,
    color: "rgba(255,255,255,.22)",
    size: 28
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      opacity: .9
    }
  }, "+9 going")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "8px 14px",
      borderRadius: 100,
      background: "#fff",
      color: "rgb(36,84,255)",
      fontWeight: 500,
      fontSize: 14,
      letterSpacing: "-.02em"
    }
  }, "RSVP")));
}

// Schedule list event row
function EventRow({
  event,
  onOpen
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onOpen,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14,
      padding: "12px 16px",
      cursor: "pointer",
      borderBottom: "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 48,
      textAlign: "center",
      padding: "6px 0",
      borderRadius: 10,
      background: event.kind === "Game" ? "rgb(235,242,255)" : "rgb(249,249,249)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 10,
      fontWeight: 500,
      color: event.kind === "Game" ? "rgb(36,84,255)" : "rgb(112,112,123)",
      letterSpacing: ".06em"
    }
  }, event.month), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 500,
      color: event.kind === "Game" ? "rgb(36,84,255)" : "#000",
      lineHeight: "22px",
      letterSpacing: "-.02em"
    }
  }, event.day)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em",
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap"
    }
  }, event.title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "rgb(112,112,123)",
      marginTop: 2,
      letterSpacing: "-.02em"
    }
  }, event.time, " \xB7 ", event.where)), event.score && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      fontWeight: 500,
      padding: "4px 10px",
      borderRadius: 100,
      background: event.scoreTone === "W" ? "rgba(48,164,108,.12)" : "rgba(243,0,13,.08)",
      color: event.scoreTone === "W" ? "rgb(24,121,78)" : "rgb(198,42,47)"
    }
  }, event.score), /*#__PURE__*/React.createElement("span", {
    className: "material-symbols-rounded",
    style: {
      fontSize: 20,
      color: "rgb(185,187,198)"
    }
  }, "chevron_right"));
}

// RSVP segmented control
function RsvpControl({
  value,
  onChange
}) {
  const opts = [{
    id: "yes",
    label: "Going",
    icon: "check_circle",
    color: "rgb(48,164,108)"
  }, {
    id: "maybe",
    label: "Maybe",
    icon: "help",
    color: "rgb(229,159,41)"
  }, {
    id: "no",
    label: "Can't",
    icon: "cancel",
    color: "rgb(243,0,13)"
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8,
      padding: "0 16px"
    }
  }, opts.map(o => {
    const on = value === o.id;
    return /*#__PURE__*/React.createElement("button", {
      key: o.id,
      onClick: () => onChange && onChange(o.id),
      style: {
        flex: 1,
        padding: "12px 8px",
        borderRadius: 12,
        border: `1.5px solid ${on ? o.color : "rgb(225,227,234)"}`,
        background: on ? `color-mix(in oklab, ${o.color} 10%, white)` : "#fff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        cursor: "pointer"
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: "material-symbols-rounded",
      style: {
        fontSize: 22,
        color: on ? o.color : "rgb(112,112,123)",
        fontVariationSettings: on ? "'FILL' 1" : "'FILL' 0"
      }
    }, o.icon), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 13,
        fontWeight: 500,
        color: on ? o.color : "rgb(32,32,32)",
        letterSpacing: "-.02em"
      }
    }, o.label));
  }));
}
window.NextEventCard = NextEventCard;
window.EventRow = EventRow;
window.RsvpControl = RsvpControl;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/EventCard.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/Login.jsx
try { (() => {
function Login({
  onContinue
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "40px 24px",
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "#fff"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 24
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/teamlinkt-mark.webp",
    style: {
      width: 72,
      height: 72,
      borderRadius: 18,
      objectFit: "contain"
    },
    alt: "TeamLinkt"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "center"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 24,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, "Welcome to TeamLinkt"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 6,
      fontSize: 14,
      color: "rgb(112,112,123)",
      letterSpacing: "-.02em"
    }
  }, "Sign in with the email or phone you used to register.")), /*#__PURE__*/React.createElement("input", {
    placeholder: "Email or phone number",
    style: {
      width: "100%",
      maxWidth: 300,
      padding: "12px 14px",
      border: "1px solid rgb(209,209,214)",
      borderRadius: 12,
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontSize: 15,
      outline: 0,
      letterSpacing: "-.02em",
      boxSizing: "border-box"
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: onContinue,
    style: {
      width: "100%",
      maxWidth: 300,
      padding: "14px",
      border: 0,
      borderRadius: 100,
      background: "rgb(36,84,255)",
      color: "#fff",
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontWeight: 500,
      fontSize: 16,
      letterSpacing: "-.02em",
      cursor: "pointer"
    }
  }, "Continue"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      width: "100%",
      maxWidth: 300,
      color: "rgb(185,187,198)",
      fontSize: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 1,
      background: "rgb(225,227,234)"
    }
  }), "or", /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 1,
      background: "rgb(225,227,234)"
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      width: "100%",
      maxWidth: 300,
      display: "flex",
      flexDirection: "column",
      gap: 10
    }
  }, [{
    label: "Continue with Apple",
    icon: ""
  }, {
    label: "Continue with Google",
    icon: ""
  }].map(o => /*#__PURE__*/React.createElement("button", {
    key: o.label,
    onClick: onContinue,
    style: {
      padding: "12px",
      border: "1px solid rgb(225,227,234)",
      borderRadius: 100,
      background: "#fff",
      fontFamily: "'Be Vietnam Pro',sans-serif",
      fontWeight: 500,
      fontSize: 15,
      letterSpacing: "-.02em",
      cursor: "pointer",
      color: "#000"
    }
  }, o.label)))), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "center",
      fontSize: 12,
      color: "rgb(112,112,123)",
      lineHeight: "18px",
      letterSpacing: "-.02em"
    }
  }, "By continuing, you agree to TeamLinkt's", /*#__PURE__*/React.createElement("br", null), "Terms and Privacy Policy."));
}
window.Login = Login;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/Login.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/RosterList.jsx
try { (() => {
function RosterList({
  players
}) {
  return /*#__PURE__*/React.createElement("div", null, players.map((p, i) => /*#__PURE__*/React.createElement("div", {
    key: p.id,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14,
      padding: "12px 16px",
      borderBottom: i === players.length - 1 ? "none" : "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      textAlign: "center"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 500,
      color: "rgb(36,84,255)",
      lineHeight: "22px",
      letterSpacing: "-.02em"
    }
  }, "#", p.num)), /*#__PURE__*/React.createElement(MAvatar, {
    initials: p.initials,
    size: 40
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, p.name), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "rgb(112,112,123)",
      letterSpacing: "-.02em"
    }
  }, p.pos)), p.captain && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      fontWeight: 500,
      padding: "3px 8px",
      borderRadius: 6,
      background: "rgba(229,159,41,.15)",
      color: "rgb(176,113,17)",
      letterSpacing: ".04em"
    }
  }, "C"))));
}
window.RosterList = RosterList;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/RosterList.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/Screen.jsx
try { (() => {
function ScreenHeader({
  title,
  left,
  right,
  large
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "8px 16px 12px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      minHeight: 44,
      background: "#fff",
      borderBottom: large ? "none" : "1px solid rgb(225,227,234)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 40
    }
  }, left), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: "center",
      fontSize: 17,
      fontWeight: 500,
      color: "#000",
      letterSpacing: "-.02em"
    }
  }, !large && title), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 40,
      textAlign: "right"
    }
  }, right));
}
function LargeTitle({
  children,
  sub
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "4px 16px 12px"
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontWeight: 500,
      fontSize: 32,
      lineHeight: "36px",
      letterSpacing: "-.02em",
      color: "#000"
    }
  }, children), sub && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 4,
      fontSize: 14,
      color: "rgb(112,112,123)",
      letterSpacing: "-.02em"
    }
  }, sub));
}
function MAvatar({
  initials,
  color = "rgb(36,84,255)",
  size = 36
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: size,
      height: size,
      borderRadius: "50%",
      background: color,
      color: "#fff",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: Math.round(size * .36),
      fontWeight: 500,
      letterSpacing: "-.02em",
      flexShrink: 0
    }
  }, initials);
}
window.ScreenHeader = ScreenHeader;
window.LargeTitle = LargeTitle;
window.MAvatar = MAvatar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/Screen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/TabBar.jsx
try { (() => {
// Bottom tab bar — 5 tabs, active = brand blue
function TabBar({
  active,
  onChange
}) {
  const tabs = [{
    id: "home",
    label: "Home",
    icon: "home"
  }, {
    id: "schedule",
    label: "Schedule",
    icon: "event"
  }, {
    id: "chat",
    label: "Chat",
    icon: "chat_bubble"
  }, {
    id: "roster",
    label: "Roster",
    icon: "groups"
  }, {
    id: "more",
    label: "More",
    icon: "more_horiz"
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      borderTop: "1px solid rgb(225,227,234)",
      background: "#fff",
      paddingBottom: 8
    }
  }, tabs.map(t => {
    const on = active === t.id;
    return /*#__PURE__*/React.createElement("div", {
      key: t.id,
      onClick: () => onChange && onChange(t.id),
      style: {
        flex: 1,
        padding: "10px 0 6px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 2,
        cursor: "pointer",
        userSelect: "none"
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: "material-symbols-rounded",
      style: {
        fontSize: 24,
        color: on ? "rgb(36,84,255)" : "rgb(112,112,123)",
        fontVariationSettings: on ? "'FILL' 1" : "'FILL' 0"
      }
    }, t.icon), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 11,
        fontWeight: 500,
        color: on ? "rgb(36,84,255)" : "rgb(112,112,123)",
        letterSpacing: "-.02em"
      }
    }, t.label));
  }));
}
window.TabBar = TabBar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/TabBar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/team-app/ios-frame.jsx
try { (() => {
// iOS.jsx — Simplified iOS 26 (Liquid Glass) device frame
// Based on the iOS 26 UI Kit + Figma status bar spec. No assets, no deps.
// Exports: IOSDevice, IOSStatusBar, IOSNavBar, IOSGlassPill, IOSList, IOSListRow, IOSKeyboard

// ─────────────────────────────────────────────────────────────
// Status bar
// ─────────────────────────────────────────────────────────────
function IOSStatusBar({
  dark = false,
  time = '9:41'
}) {
  const c = dark ? '#fff' : '#000';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 154,
      alignItems: 'center',
      justifyContent: 'center',
      padding: '21px 24px 19px',
      boxSizing: 'border-box',
      position: 'relative',
      zIndex: 20,
      width: '100%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 22,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      paddingTop: 1.5
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: '-apple-system, "SF Pro", system-ui',
      fontWeight: 590,
      fontSize: 17,
      lineHeight: '22px',
      color: c
    }
  }, time)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 22,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 7,
      paddingTop: 1,
      paddingRight: 1
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "19",
    height: "12",
    viewBox: "0 0 19 12"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "0",
    y: "7.5",
    width: "3.2",
    height: "4.5",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "4.8",
    y: "5",
    width: "3.2",
    height: "7",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "9.6",
    y: "2.5",
    width: "3.2",
    height: "9.5",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "14.4",
    y: "0",
    width: "3.2",
    height: "12",
    rx: "0.7",
    fill: c
  })), /*#__PURE__*/React.createElement("svg", {
    width: "17",
    height: "12",
    viewBox: "0 0 17 12"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M8.5 3.2C10.8 3.2 12.9 4.1 14.4 5.6L15.5 4.5C13.7 2.7 11.2 1.5 8.5 1.5C5.8 1.5 3.3 2.7 1.5 4.5L2.6 5.6C4.1 4.1 6.2 3.2 8.5 3.2Z",
    fill: c
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8.5 6.8C9.9 6.8 11.1 7.3 12 8.2L13.1 7.1C11.8 5.9 10.2 5.1 8.5 5.1C6.8 5.1 5.2 5.9 3.9 7.1L5 8.2C5.9 7.3 7.1 6.8 8.5 6.8Z",
    fill: c
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "8.5",
    cy: "10.5",
    r: "1.5",
    fill: c
  })), /*#__PURE__*/React.createElement("svg", {
    width: "27",
    height: "13",
    viewBox: "0 0 27 13"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "0.5",
    y: "0.5",
    width: "23",
    height: "12",
    rx: "3.5",
    stroke: c,
    strokeOpacity: "0.35",
    fill: "none"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "2",
    y: "2",
    width: "20",
    height: "9",
    rx: "2",
    fill: c
  }), /*#__PURE__*/React.createElement("path", {
    d: "M25 4.5V8.5C25.8 8.2 26.5 7.2 26.5 6.5C26.5 5.8 25.8 4.8 25 4.5Z",
    fill: c,
    fillOpacity: "0.4"
  }))));
}

// ─────────────────────────────────────────────────────────────
// Liquid glass pill — blur + tint + shine
// ─────────────────────────────────────────────────────────────
function IOSGlassPill({
  children,
  dark = false,
  style = {}
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      height: 44,
      minWidth: 44,
      borderRadius: 9999,
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: dark ? '0 2px 6px rgba(0,0,0,0.35), 0 6px 16px rgba(0,0,0,0.2)' : '0 1px 3px rgba(0,0,0,0.07), 0 3px 10px rgba(0,0,0,0.06)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 9999,
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      background: dark ? 'rgba(120,120,128,0.28)' : 'rgba(255,255,255,0.5)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 9999,
      boxShadow: dark ? 'inset 1.5px 1.5px 1px rgba(255,255,255,0.15), inset -1px -1px 1px rgba(255,255,255,0.08)' : 'inset 1.5px 1.5px 1px rgba(255,255,255,0.7), inset -1px -1px 1px rgba(255,255,255,0.4)',
      border: dark ? '0.5px solid rgba(255,255,255,0.15)' : '0.5px solid rgba(0,0,0,0.06)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 1,
      display: 'flex',
      alignItems: 'center',
      padding: '0 4px'
    }
  }, children));
}

// ─────────────────────────────────────────────────────────────
// Navigation bar — glass pills + large title
// ─────────────────────────────────────────────────────────────
function IOSNavBar({
  title = 'Title',
  dark = false,
  trailingIcon = true
}) {
  const muted = dark ? 'rgba(255,255,255,0.6)' : '#404040';
  const text = dark ? '#fff' : '#000';
  const pillIcon = content => /*#__PURE__*/React.createElement(IOSGlassPill, {
    dark: dark
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      height: 36,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, content));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      paddingTop: 62,
      paddingBottom: 10,
      position: 'relative',
      zIndex: 5
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px'
    }
  }, pillIcon(/*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "20",
    viewBox: "0 0 12 20",
    fill: "none",
    style: {
      marginLeft: -1
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M10 2L2 10l8 8",
    stroke: muted,
    strokeWidth: "2.5",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }))), trailingIcon && pillIcon(/*#__PURE__*/React.createElement("svg", {
    width: "22",
    height: "6",
    viewBox: "0 0 22 6"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "3",
    cy: "3",
    r: "2.5",
    fill: muted
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "3",
    r: "2.5",
    fill: muted
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "19",
    cy: "3",
    r: "2.5",
    fill: muted
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '0 16px',
      fontFamily: '-apple-system, system-ui',
      fontSize: 34,
      fontWeight: 700,
      lineHeight: '41px',
      color: text,
      letterSpacing: 0.4
    }
  }, title));
}

// ─────────────────────────────────────────────────────────────
// Grouped list (inset card, r:26) + row (52px)
// ─────────────────────────────────────────────────────────────
function IOSListRow({
  title,
  detail,
  icon,
  chevron = true,
  isLast = false,
  dark = false
}) {
  const text = dark ? '#fff' : '#000';
  const sec = dark ? 'rgba(235,235,245,0.6)' : 'rgba(60,60,67,0.6)';
  const ter = dark ? 'rgba(235,235,245,0.3)' : 'rgba(60,60,67,0.3)';
  const sep = dark ? 'rgba(84,84,88,0.65)' : 'rgba(60,60,67,0.12)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      minHeight: 52,
      padding: '0 16px',
      position: 'relative',
      fontFamily: '-apple-system, system-ui',
      fontSize: 17,
      letterSpacing: -0.43
    }
  }, icon && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 30,
      height: 30,
      borderRadius: 7,
      background: icon,
      marginRight: 12,
      flexShrink: 0
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      color: text
    }
  }, title), detail && /*#__PURE__*/React.createElement("span", {
    style: {
      color: sec,
      marginRight: 6
    }
  }, detail), chevron && /*#__PURE__*/React.createElement("svg", {
    width: "8",
    height: "14",
    viewBox: "0 0 8 14",
    style: {
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M1 1l6 6-6 6",
    stroke: ter,
    strokeWidth: "2",
    fill: "none",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  })), !isLast && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 0,
      right: 0,
      left: icon ? 58 : 16,
      height: 0.5,
      background: sep
    }
  }));
}
function IOSList({
  header,
  children,
  dark = false
}) {
  const hc = dark ? 'rgba(235,235,245,0.6)' : 'rgba(60,60,67,0.6)';
  const bg = dark ? '#1C1C1E' : '#fff';
  return /*#__PURE__*/React.createElement("div", null, header && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: '-apple-system, system-ui',
      fontSize: 13,
      color: hc,
      textTransform: 'uppercase',
      padding: '8px 36px 6px',
      letterSpacing: -0.08
    }
  }, header), /*#__PURE__*/React.createElement("div", {
    style: {
      background: bg,
      borderRadius: 26,
      margin: '0 16px',
      overflow: 'hidden'
    }
  }, children));
}

// ─────────────────────────────────────────────────────────────
// Device frame
// ─────────────────────────────────────────────────────────────
function IOSDevice({
  children,
  width = 402,
  height = 874,
  dark = false,
  title,
  keyboard = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width,
      height,
      borderRadius: 48,
      overflow: 'hidden',
      position: 'relative',
      background: dark ? '#000' : '#F2F2F7',
      boxShadow: '0 40px 80px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.12)',
      fontFamily: '-apple-system, system-ui, sans-serif',
      WebkitFontSmoothing: 'antialiased'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 11,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 126,
      height: 37,
      borderRadius: 24,
      background: '#000',
      zIndex: 50
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 10
    }
  }, /*#__PURE__*/React.createElement(IOSStatusBar, {
    dark: dark
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }
  }, title !== undefined && /*#__PURE__*/React.createElement(IOSNavBar, {
    title: title,
    dark: dark
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflow: 'auto'
    }
  }, children), keyboard && /*#__PURE__*/React.createElement(IOSKeyboard, {
    dark: dark
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 60,
      height: 34,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-end',
      paddingBottom: 8,
      pointerEvents: 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 139,
      height: 5,
      borderRadius: 100,
      background: dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.25)'
    }
  })));
}

// ─────────────────────────────────────────────────────────────
// Keyboard — iOS 26 liquid glass
// ─────────────────────────────────────────────────────────────
function IOSKeyboard({
  dark = false
}) {
  const glyph = dark ? 'rgba(255,255,255,0.7)' : '#595959';
  const sugg = dark ? 'rgba(255,255,255,0.6)' : '#333';
  const keyBg = dark ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.85)';

  // special-key icons
  const icons = {
    shift: /*#__PURE__*/React.createElement("svg", {
      width: "19",
      height: "17",
      viewBox: "0 0 19 17"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M9.5 1L1 9.5h4.5V16h8V9.5H18L9.5 1z",
      fill: glyph
    })),
    del: /*#__PURE__*/React.createElement("svg", {
      width: "23",
      height: "17",
      viewBox: "0 0 23 17"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M7 1h13a2 2 0 012 2v11a2 2 0 01-2 2H7l-6-7.5L7 1z",
      fill: "none",
      stroke: glyph,
      strokeWidth: "1.6",
      strokeLinejoin: "round"
    }), /*#__PURE__*/React.createElement("path", {
      d: "M10 5l7 7M17 5l-7 7",
      stroke: glyph,
      strokeWidth: "1.6",
      strokeLinecap: "round"
    })),
    ret: /*#__PURE__*/React.createElement("svg", {
      width: "20",
      height: "14",
      viewBox: "0 0 20 14"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M18 1v6H4m0 0l4-4M4 7l4 4",
      fill: "none",
      stroke: "#fff",
      strokeWidth: "1.8",
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }))
  };
  const key = (content, {
    w,
    flex,
    ret,
    fs = 25,
    k
  } = {}) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      height: 42,
      borderRadius: 8.5,
      flex: flex ? 1 : undefined,
      width: w,
      minWidth: 0,
      background: ret ? '#08f' : keyBg,
      boxShadow: '0 1px 0 rgba(0,0,0,0.075)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, "SF Compact", system-ui',
      fontSize: fs,
      fontWeight: 458,
      color: ret ? '#fff' : glyph
    }
  }, content);
  const row = (keys, pad = 0) => /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6.5,
      justifyContent: 'center',
      padding: `0 ${pad}px`
    }
  }, keys.map(l => key(l, {
    flex: true,
    k: l
  })));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 15,
      borderRadius: 27,
      overflow: 'hidden',
      padding: '11px 0 2px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      boxShadow: dark ? '0 -2px 20px rgba(0,0,0,0.09)' : '0 -1px 6px rgba(0,0,0,0.018), 0 -3px 20px rgba(0,0,0,0.012)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 27,
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      background: dark ? 'rgba(120,120,128,0.14)' : 'rgba(255,255,255,0.25)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 27,
      boxShadow: dark ? 'inset 1.5px 1.5px 1px rgba(255,255,255,0.15)' : 'inset 1.5px 1.5px 1px rgba(255,255,255,0.7), inset -1px -1px 1px rgba(255,255,255,0.4)',
      border: dark ? '0.5px solid rgba(255,255,255,0.15)' : '0.5px solid rgba(0,0,0,0.06)',
      pointerEvents: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 20,
      alignItems: 'center',
      padding: '8px 22px 13px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    }
  }, ['"The"', 'the', 'to'].map((w, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: i
  }, i > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 1,
      height: 25,
      background: '#ccc',
      opacity: 0.3
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'center',
      fontFamily: '-apple-system, system-ui',
      fontSize: 17,
      color: sugg,
      letterSpacing: -0.43,
      lineHeight: '22px'
    }
  }, w)))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 13,
      padding: '0 6.5px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    }
  }, row(['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']), row(['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'], 20), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 14.25,
      alignItems: 'center'
    }
  }, key(icons.shift, {
    w: 45,
    k: 'shift'
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6.5,
      flex: 1
    }
  }, ['z', 'x', 'c', 'v', 'b', 'n', 'm'].map(l => key(l, {
    flex: true,
    k: l
  }))), key(icons.del, {
    w: 45,
    k: 'del'
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6,
      alignItems: 'center'
    }
  }, key('ABC', {
    w: 92.25,
    fs: 18,
    k: 'abc'
  }), key('', {
    flex: true,
    k: 'space'
  }), key(icons.ret, {
    w: 92.25,
    ret: true,
    k: 'ret'
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 56,
      width: '100%',
      position: 'relative'
    }
  }));
}
Object.assign(window, {
  IOSDevice,
  IOSStatusBar,
  IOSNavBar,
  IOSGlassPill,
  IOSList,
  IOSListRow,
  IOSKeyboard
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/team-app/ios-frame.jsx", error: String((e && e.message) || e) }); }

})();

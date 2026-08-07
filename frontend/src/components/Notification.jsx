import { useEffect } from "react";
import { CloseIcon, ErrorIcon, AutoAwesomeIcon } from "./Icons";
import { CheckCircle2Icon } from "lucide-react";

/**
 * Premium toast notification component.
 * @param {string} message - The message to display
 * @param {string} type - 'error', 'success', or 'info'
 * @param {Function} onClose - Close handler
 */
export default function Notification({ message, type = "error", onClose }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const getIcon = () => {
    switch (type) {
      case "success": return <CheckCircle2Icon sx={{ color: "#3fb950" }} />;
      case "info": return <AutoAwesomeIcon sx={{ color: "#58a6ff" }} />;
      default: return <ErrorIcon sx={{ color: "#f85149" }} />;
    }
  };

  const getBorderColor = () => {
    switch (type) {
      case "success": return "rgba(63,185,80,0.3)";
      case "info": return "rgba(88,166,255,0.3)";
      default: return "rgba(248,81,73,0.3)";
    }
  };

  return (
    <div style={{
      position: "fixed",
      bottom: "24px",
      right: "24px",
      zIndex: 10001,
      minWidth: "320px",
      maxWidth: "420px",
      background: "rgba(13, 17, 23, 0.95)",
      backdropFilter: "blur(20px)",
      border: `1px solid ${getBorderColor()}`,
      borderRadius: "14px",
      padding: "16px",
      display: "flex",
      alignItems: "center",
      gap: "12px",
      boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
      animation: "toastIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards",
    }}>
      <style>{`
        @keyframes toastIn {
          from { opacity: 0; transform: translateY(40px) scale(0.9); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
      
      <div style={{ flexShrink: 0 }}>
        {getIcon()}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ 
          margin: 0, 
          fontSize: "0.85rem", 
          fontWeight: 600, 
          color: "#e6edf3",
          lineHeight: 1.4,
        }}>
          {message}
        </p>
      </div>

      <button 
        onClick={onClose}
        style={{
          background: "none",
          border: "none",
          color: "#6e7681",
          cursor: "pointer",
          padding: 4,
          display: "flex",
          borderRadius: "6px",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
        onMouseLeave={e => e.currentTarget.style.background = "none"}
      >
        <CloseIcon iconProps={{ sx: { fontSize: 16 } }} />
      </button>
    </div>
  );
}

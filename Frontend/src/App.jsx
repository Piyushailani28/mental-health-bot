import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      setIsTyping(true);
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      const data = await res.json();

      // Show typing indicator
      setMessages((prev) => [...prev, { sender: "bot", text: "..." }]);

      // Wait 200ms before replacing "..." with actual reply
      await new Promise((resolve) => setTimeout(resolve, 1000));

      setMessages((prev) => [
        ...prev.slice(0, -1),
        { sender: "bot", text: data.reply },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Error connecting to the server." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100 text-gray-900">
      <header className="bg-white shadow p-4 text-center text-xl font-semibold">
        <div className="text-3xl font-bold mb-2">BetterMind</div>
        Support
      </header>
      <main className="flex-1 overflow-auto p-4">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((msg, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${
                msg.sender === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.2 }}
                className={`px-4 py-2 rounded-lg shadow-md max-w-xs ${
                  msg.sender === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-gray-900"
                }`}
              >
                {msg.text}
              </motion.div>
            </motion.div>
          ))}
          {isTyping && (
            <div className="flex justify-start animate-pulse">
              <div className="px-4 py-2 rounded-lg shadow-md max-w-xs bg-gray-200 text-gray-900">
                Typing...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </main>
      <footer className="p-4 bg-white shadow flex justify-center">
        <div className="flex w-full max-w-2xl">
          <motion.input
            className="flex-1 p-3 border border-gray-300 rounded-l-full focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-900"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            whileFocus={{ scale: 1.02 }}
          />
          <motion.button
            className="bg-blue-500 text-white px-6 rounded-r-full hover:bg-blue-600 transition duration-200"
            onClick={sendMessage}
            whileTap={{ scale: 0.95 }}
          >
            Send
          </motion.button>
        </div>
      </footer>
    </div>
  );
}

export default App;

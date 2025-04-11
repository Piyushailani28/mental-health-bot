import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  messages: [],
};

export const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    setMessages: (state, action) => {
      state.messages = action.payload;
    },
    resetChat: (state) => {
      state.messages = [];
    },
  },
});

export const { addMessage, setMessages, resetChat } = chatSlice.actions;
export default chatSlice.reducer;

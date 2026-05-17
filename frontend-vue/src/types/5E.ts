export interface ChatResponse {
    role: 'user' | 'assistant',
    content: string,
    buttons?: Button[],
    resources?: Resource[],
    tests?: Test[],
    timestamp: number,
}

export interface Button {
    show_text: string,
    send_text: string,
}

export interface Resource {
    show_text: string,
    id: string,
}

export interface Test {
    show_text: string,
    id: string,
}
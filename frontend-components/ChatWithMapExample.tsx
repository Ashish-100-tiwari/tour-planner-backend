import React, { useState } from 'react';
import MapWithZoom from './MapWithZoom';

/**
 * Example usage of MapWithZoom component
 * 
 * This shows how to integrate the map zoom component into your chat interface
 */

const ChatWithMap: React.FC = () => {
    const [messages, setMessages] = useState<any[]>([]);
    const [authToken, setAuthToken] = useState<string>(''); // Get from your auth context

    // Example: Detect when a message contains journey information
    const renderMessage = (message: any) => {
        // If message has journey details (origin and destination)
        if (message.journey_details) {
            return (
                <div className="message-with-map">
                    <div className="message-text">
                        {message.content}
                    </div>

                    {/* Render the map with zoom controls */}
                    <MapWithZoom
                        origin={message.journey_details.origin}
                        destination={message.journey_details.destination}
                        authToken={authToken}
                        apiBaseUrl="http://localhost:8000"
                        initialZoom={null} // Start with auto-fit
                        onZoomChange={(zoom) => {
                            console.log('Zoom changed to:', zoom);
                        }}
                    />
                </div>
            );
        }

        // Regular message without map
        return (
            <div className="message-text">
                {message.content}
            </div>
        );
    };

    return (
        <div className="chat-container">
            {messages.map((message, index) => (
                <div key={index} className={`message ${message.role}`}>
                    {renderMessage(message)}
                </div>
            ))}
        </div>
    );
};

export default ChatWithMap;

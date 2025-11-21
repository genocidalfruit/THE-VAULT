import { promises as fs } from 'fs';
import { promisify } from 'util';
import { exec } from 'child_process';

const execPromise = promisify(exec);

const API_KEY = process.env.GEMINI_API_KEY;
const MODEL_NAME = 'gemini-2.5-flash-preview-09-2025';
const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL_NAME}:generateContent?key=${API_KEY}`;
const MAX_RETRIES = 5;

// System instruction: Crucial for ensuring the model only modifies headings
const SYSTEM_INSTRUCTION = `You are a specialized Markdown formatter for Obsidian notes.
Your task is to review the provided Markdown content and ONLY modify the headings (H1 to H6) by prepending a single, relevant, and professional-looking emoji to the heading text.
DO NOT change the heading level or the text of the heading, except to add the emoji.
DO NOT modify any other part of the document, including YAML front matter, links, code blocks, lists, or regular paragraph text.
The output MUST be valid, complete Markdown content, including all original front matter and content, with only the headings modified by the addition of an emoji.

Example:
Original Heading: # Daily Review
Modified Heading: # 🗓️ Daily Review

Original Heading: ## Project Planning
Modified Heading: ## 🚀 Project Planning

Original Heading: ### Key Action Items
Modified Heading: ### 📌 Key Action Items
`;

/**
 * Handles the LLM API call with exponential backoff.
 * @param {string} content The Markdown content to send to the LLM.
 * @returns {Promise<string>} The formatted Markdown content.
 */
async function callGeminiApi(content) {
    const payload = {
        contents: [{ parts: [{ text: content }] }],
        systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
        tools: [{ "google_search": {} }], // Use grounding for contextually relevant emojis
    };

    let attempt = 0;
    while (attempt < MAX_RETRIES) {
        try {
            console.log(`Attempt ${attempt + 1}: Calling Gemini API for formatting...`);
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const result = await response.json();
                const text = result.candidates?.[0]?.content?.parts?.[0]?.text;
                if (text) {
                    return text;
                } else {
                    throw new Error("API response was successful but text content is missing.");
                }
            } else {
                const errorBody = await response.text();
                throw new Error(`API returned status ${response.status}: ${errorBody}`);
            }
        } catch (error) {
            console.warn(`API call failed on attempt ${attempt + 1}: ${error.message}`);
            attempt++;
            if (attempt >= MAX_RETRIES) {
                console.error("Max retries reached. Skipping file formatting.");
                // Return original content to prevent data loss
                return content;
            }
            const delay = Math.pow(2, attempt) * 1000 + Math.random() * 1000;
            console.log(`Retrying in ${Math.round(delay / 1000)}s...`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    return content;
}

/**
 * Finds all Markdown files recursively and returns their paths.
 * @returns {Promise<string[]>} Array of file paths.
 */
async function findMarkdownFiles() {
    try {
        // Use find to locate all .md files, excluding .git and node_modules directories
        const { stdout } = await execPromise(`find . -name "*.md" -type f -not -path "./.git/*" -not -path "./node_modules/*"`);
        return stdout.split('\n').map(p => p.trim()).filter(p => p.length > 0);
    } catch (error) {
        console.error("Error finding markdown files:", error);
        return [];
    }
}

async function processFiles() {
    if (!API_KEY) {
        console.error("FATAL: GEMINI_API_KEY is not set. Cannot run LLM formatting step.");
        return;
    }

    const files = await findMarkdownFiles();
    if (files.length === 0) {
        console.log("No markdown files found to process.");
        return;
    }

    console.log(`Found ${files.length} markdown files to process.`);

    for (const filePath of files) {
        try {
            console.log(`Processing: ${filePath}`);
            const originalContent = await fs.readFile(filePath, 'utf8');
            
            if (originalContent.trim() === '') {
                console.log(`Skipping empty file: ${filePath}`);
                continue;
            }
            
            const formattedContent = await callGeminiApi(originalContent);
            
            if (formattedContent !== originalContent) {
                await fs.writeFile(filePath, formattedContent, 'utf8');
                console.log(`Successfully formatted and updated: ${filePath}`);
            } else {
                console.log(`No changes made to: ${filePath}`);
            }

        } catch (error) {
            console.error(`Failed to process ${filePath}:`, error.message);
        }
    }
}

// Execute the main function
processFiles().catch(error => {
    console.error("An unhandled error occurred during file processing:", error);
    process.exit(1);
});
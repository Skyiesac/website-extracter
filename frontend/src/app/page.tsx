'use client';

import { useState } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export default function Home() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generatedHtml, setGeneratedHtml] = useState('');
  const [isSmall, setIsSmall] = useState(true);
  const [previewId, setPreviewId] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setGeneratedHtml('');
    setPreviewId('');

    try {
      const response = await fetch(`${API_BASE_URL}/clone-website`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, is_small: isSmall }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate HTML');
      }

      const data = await response.json();
      setGeneratedHtml(data.html);
      setPreviewId(data.preview_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = () => {
    if (previewId) {
      window.open(`${API_BASE_URL}/preview/${previewId}`, '_blank');
    }
  };

  return (
    <main className="relative min-h-screen bg-gradient-to-b from-black via-black/95 to-black/90 text-white flex items-center justify-center p-8 font-sans">
      <header className="absolute top-8 right-8">
        <div className="flex items-center gap-6">
          <a
            href="https://www.linkedin.com/in/sachi-0abjain/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-white/60 hover:text-white transition-colors"
            title="LinkedIn"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6"
            >
              <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
              <rect width="4" height="12" x="2" y="9" />
              <circle cx="4" cy="4" r="2" />
            </svg>
          </a>
          <a
            href="https://github.com/Skyiesac"
            target="_blank"
            rel="noopener noreferrer"
            className="text-white/60 hover:text-white transition-colors"
            title="GitHub"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6"
            >
              <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
              <path d="M9 18c-4.51 2-5-2-7-2" />
            </svg>
          </a>
          <a
            href="mailto:jainsachi1202@gmail.com"
            className="text-white/60 hover:text-white transition-colors"
            title="Email"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6"
            >
              <rect width="20" height="16" x="2" y="4" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
          </a>
        </div>
      </header>
      <div className="w-full max-w-2xl backdrop-blur-md bg-white/5 p-10 rounded-3xl border border-white/10 shadow-2xl shadow-white/5">
        <div className="space-y-2 mb-16 text-center">
          <h1 className="text-6xl font-light tracking-tight bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
            Website Cloner
          </h1>
          <p className="text-white/60 text-lg">Transform any website into HTML</p>
        </div>
        
        <form onSubmit={handleSubmit} className="mb-12">
          <div className="flex flex-col gap-6">
            <div className="relative group">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter website URL..."
                className="w-full px-8 py-5 bg-black/40 border-2 border-white/20 rounded-2xl focus:ring-2 focus:ring-white/30 focus:border-white/30 outline-none text-white placeholder-white/50 text-lg backdrop-blur-sm transition-all duration-300 group-hover:border-white/30"
                required
              />
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-white/0 via-white/5 to-white/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
            </div>

            <div className="flex gap-4 justify-center">
              <button
                type="button"
                onClick={() => setIsSmall(true)}
                className={`px-6 py-3 rounded-xl transition-all duration-300 ${
                  isSmall 
                    ? 'bg-white text-black' 
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Small Website
              </button>
              <button
                type="button"
                onClick={() => setIsSmall(false)}
                className={`px-6 py-3 rounded-xl transition-all duration-300 ${
                  !isSmall 
                    ? 'bg-white text-black' 
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Large Website
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-8 py-5 bg-white text-black rounded-2xl hover:bg-white/90 focus:ring-2 focus:ring-white/30 focus:ring-offset-2 focus:ring-offset-black/95 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {isSmall ? 'Generating with Gemini...' : 'Cloning with Playwright...'}
                </span>
              ) : 'Clone Website'}
            </button>
          </div>
        </form>

        {error && (
          <div className="p-6 mb-8 bg-red-500/10 border border-red-500/20 rounded-2xl backdrop-blur-sm animate-fade-in">
            <p className="text-red-400/90 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </p>
          </div>
        )}

        {generatedHtml && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-light text-white/80">Generated HTML</h2>
              <div className="flex gap-3">
                <button
                  onClick={handlePreview}
                  className="px-6 py-3 bg-white/10 text-white rounded-xl hover:bg-white/20 focus:ring-2 focus:ring-white/30 focus:ring-offset-2 focus:ring-offset-black/95 transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  Preview
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(generatedHtml)}
                  className="px-6 py-3 bg-white text-black rounded-xl hover:bg-white/90 focus:ring-2 focus:ring-white/30 focus:ring-offset-2 focus:ring-offset-black/95 transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  Copy
                </button>
              </div>
            </div>
            <pre className="font-mono p-6 bg-black/40 text-white/80 rounded-2xl overflow-x-auto border border-white/10 backdrop-blur-sm text-sm">
              <code>{generatedHtml}</code>
            </pre>
          </div>
        )}
      </div>
      <footer className="absolute bottom-8 text-white/40 text-sm">
        Developed by Sachi Jain
      </footer>
    </main>
  );
} 
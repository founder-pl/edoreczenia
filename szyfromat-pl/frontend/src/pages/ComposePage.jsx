import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { messagesApi } from '../services/api.jsx';
import { 
  Send, Paperclip, X, ArrowLeft, Save, Trash2,
  User, AlertCircle, CheckCircle
} from 'lucide-react';

export default function ComposePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Obsługa Reply i Forward z przekazanego state
  useEffect(() => {
    if (location.state) {
      if (location.state.recipient) {
        setRecipient(location.state.recipient);
      }
      if (location.state.subject) {
        setSubject(location.state.subject);
      }
      if (location.state.content) {
        setContent(location.state.content);
      }
    }
  }, [location.state]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSending(true);

    try {
      await messagesApi.send({
        recipient,
        subject,
        content,
        attachments: attachments.map(a => a.name)
      });
      setSuccess(true);
      setTimeout(() => navigate('/sent'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Błąd wysyłania wiadomości');
    } finally {
      setSending(false);
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setAttachments(prev => [...prev, ...files]);
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  if (success) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="text-center animate-fadeIn">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={32} className="text-green-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Wiadomość wysłana!
          </h2>
          <p className="text-gray-500">
            Przekierowuję do folderu Wysłane...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-semibold text-pp-dark">
            Nowa wiadomość
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button 
            className="btn-secondary flex items-center gap-2"
            onClick={() => {/* Save draft */}}
          >
            <Save size={18} />
            <span className="hidden sm:inline">Zapisz</span>
          </button>
          <button 
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-red-500"
            onClick={() => navigate(-1)}
          >
            <Trash2 size={20} />
          </button>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
        <div className="p-4 space-y-4 border-b border-gray-200">
          {error && (
            <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-xl animate-fadeIn">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          {/* Recipient */}
          <div className="flex items-center gap-4">
            <label className="w-20 text-sm font-medium text-gray-500">Do:</label>
            <div className="flex-1 relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="Adres ADE odbiorcy (np. AE:PL-XXXXX-XXXXX-XXXXX-XX)"
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pp-red focus:border-transparent"
                required
              />
            </div>
          </div>

          {/* Subject */}
          <div className="flex items-center gap-4">
            <label className="w-20 text-sm font-medium text-gray-500">Temat:</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Temat wiadomości"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pp-red focus:border-transparent"
              required
            />
          </div>

          {/* Attachments */}
          {attachments.length > 0 && (
            <div className="flex items-start gap-4">
              <label className="w-20 text-sm font-medium text-gray-500 pt-2">Załączniki:</label>
              <div className="flex-1 flex flex-wrap gap-2">
                {attachments.map((file, index) => (
                  <div 
                    key={index}
                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full text-sm"
                  >
                    <Paperclip size={14} />
                    <span className="max-w-[150px] truncate">{file.name}</span>
                    <button 
                      type="button"
                      onClick={() => removeAttachment(index)}
                      className="p-0.5 hover:bg-gray-200 rounded-full"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 p-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Treść wiadomości..."
            className="w-full h-full resize-none border-0 focus:outline-none focus:ring-0 text-gray-700"
            required
          />
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <label className="p-2 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer">
              <Paperclip size={20} className="text-gray-500" />
              <input 
                type="file" 
                multiple 
                className="hidden" 
                onChange={handleFileChange}
              />
            </label>
            <span className="text-sm text-gray-500">
              Dodaj załącznik
            </span>
          </div>

          <button
            type="submit"
            disabled={sending}
            className="btn-primary flex items-center gap-2"
          >
            {sending ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <Send size={18} />
                <span>Wyślij</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Quick recipients */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <p className="text-xs text-gray-500 mb-2">Szybkie adresy testowe:</p>
        <div className="flex flex-wrap gap-2">
          {[
            'AE:PL-ODBIORCA-TEST-00001',
            'AE:PL-URZAD-MIAS-TOWAR-01',
            'AE:PL-SADRE-JONO-WYYYY-02'
          ].map((addr) => (
            <button
              key={addr}
              type="button"
              onClick={() => setRecipient(addr)}
              className="px-3 py-1 text-xs bg-white border border-gray-200 rounded-full hover:bg-gray-100 transition-colors"
            >
              {addr}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

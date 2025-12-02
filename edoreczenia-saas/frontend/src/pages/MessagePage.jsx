import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { messagesApi } from '../services/api.jsx';
import { 
  ArrowLeft, Reply, Forward, Trash2, Archive, Printer,
  Download, Paperclip, Clock, User, Mail, Shield, FileText
} from 'lucide-react';
import { format } from 'date-fns';
import { pl } from 'date-fns/locale';

export default function MessagePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMessage();
  }, [id]);

  const loadMessage = async () => {
    setLoading(true);
    try {
      const response = await messagesApi.getOne(id);
      setMessage(response.data);
    } catch (error) {
      console.error('Error loading message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (confirm('Czy na pewno chcesz usunąć tę wiadomość?')) {
      try {
        await messagesApi.delete(id);
        navigate('/inbox');
      } catch (error) {
        console.error('Error deleting message:', error);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pp-red"></div>
      </div>
    );
  }

  if (!message) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <Mail size={48} className="mb-4 text-gray-300" />
        <p>Nie znaleziono wiadomości</p>
        <Link to="/inbox" className="mt-4 text-pp-red hover:underline">
          Wróć do skrzynki
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button 
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <span className="text-gray-400">|</span>
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Odpowiedz">
            <Reply size={20} />
          </button>
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Przekaż">
            <Forward size={20} />
          </button>
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Archiwizuj">
            <Archive size={20} />
          </button>
          <button 
            onClick={handleDelete}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-red-500" 
            title="Usuń"
          >
            <Trash2 size={20} />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Drukuj">
            <Printer size={20} />
          </button>
        </div>
      </div>

      {/* Message content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-4xl mx-auto">
          {/* Subject */}
          <h1 className="text-2xl font-bold text-pp-dark mb-6">
            {message.subject}
          </h1>

          {/* Sender info */}
          <div className="flex items-start gap-4 mb-6 pb-6 border-b border-gray-200">
            <div className="w-12 h-12 bg-pp-dark rounded-full flex items-center justify-center text-white flex-shrink-0">
              <User size={24} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-lg">
                  {message.sender?.name || 'Nieznany nadawca'}
                </span>
                <span className={`
                  px-2 py-0.5 text-xs rounded-full
                  ${message.status === 'RECEIVED' ? 'bg-blue-100 text-blue-700' : ''}
                  ${message.status === 'READ' ? 'bg-gray-100 text-gray-600' : ''}
                  ${message.status === 'SENT' ? 'bg-green-100 text-green-700' : ''}
                `}>
                  {message.status}
                </span>
              </div>
              <div className="text-sm text-gray-500 space-y-1">
                <div className="flex items-center gap-2">
                  <Mail size={14} />
                  <span>{message.sender?.address}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock size={14} />
                  <span>
                    {message.receivedAt && format(new Date(message.receivedAt), "d MMMM yyyy 'o' HH:mm", { locale: pl })}
                  </span>
                </div>
              </div>
            </div>

            {/* EPO badge */}
            <div className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm">
              <Shield size={16} />
              <span>EPO potwierdzone</span>
            </div>
          </div>

          {/* Message body */}
          <div className="prose max-w-none mb-8">
            <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
              {message.content || 'Brak treści wiadomości.'}
            </div>
          </div>

          {/* Attachments */}
          {message.attachments?.length > 0 && (
            <div className="border-t border-gray-200 pt-6">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-4">
                <Paperclip size={16} />
                Załączniki ({message.attachments.length})
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {message.attachments.map((attachment, index) => (
                  <div 
                    key={index}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors cursor-pointer group"
                  >
                    <div className="w-10 h-10 bg-pp-red/10 rounded-lg flex items-center justify-center text-pp-red">
                      <FileText size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {attachment.filename}
                      </div>
                      <div className="text-xs text-gray-500">
                        {attachment.contentType} • {Math.round(attachment.size / 1024)} KB
                      </div>
                    </div>
                    <button className="p-2 hover:bg-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity">
                      <Download size={18} className="text-gray-500" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Message metadata */}
          <div className="mt-8 p-4 bg-gray-50 rounded-xl text-sm">
            <h4 className="font-semibold text-gray-700 mb-3">Szczegóły wiadomości</h4>
            <div className="grid grid-cols-2 gap-4 text-gray-600">
              <div>
                <span className="text-gray-400">ID wiadomości:</span>
                <span className="ml-2 font-mono">{message.id}</span>
              </div>
              <div>
                <span className="text-gray-400">Status:</span>
                <span className="ml-2">{message.status}</span>
              </div>
              <div>
                <span className="text-gray-400">Nadawca ADE:</span>
                <span className="ml-2 font-mono text-xs">{message.sender?.address}</span>
              </div>
              {message.recipient && (
                <div>
                  <span className="text-gray-400">Odbiorca ADE:</span>
                  <span className="ml-2 font-mono text-xs">{message.recipient?.address}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

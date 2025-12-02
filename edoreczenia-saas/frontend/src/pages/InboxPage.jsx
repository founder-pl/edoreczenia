import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { messagesApi } from '../services/api.jsx';
import { 
  Mail, MailOpen, Paperclip, Star, Trash2, Archive,
  ChevronLeft, ChevronRight, RefreshCw, MoreVertical,
  CheckSquare, Square
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { pl } from 'date-fns/locale';

const folderNames = {
  inbox: 'Odebrane',
  sent: 'Wysłane',
  drafts: 'Robocze',
  trash: 'Kosz',
  archive: 'Archiwum'
};

const statusLabels = {
  RECEIVED: 'Nowa',
  READ: 'Przeczytana',
  OPENED: 'Otwarta',
  SENT: 'Wysłana',
  DELIVERED: 'Doręczona'
};

export default function InboxPage({ folder = 'inbox' }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMessages, setSelectedMessages] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    loadMessages();
  }, [folder]);

  const loadMessages = async () => {
    setLoading(true);
    try {
      const response = await messagesApi.getAll(folder);
      setMessages(response.data);
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id) => {
    setSelectedMessages(prev => 
      prev.includes(id) 
        ? prev.filter(m => m !== id)
        : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedMessages.length === messages.length) {
      setSelectedMessages([]);
    } else {
      setSelectedMessages(messages.map(m => m.id));
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return format(date, 'HH:mm');
    } else if (diffDays < 7) {
      return formatDistanceToNow(date, { addSuffix: true, locale: pl });
    } else {
      return format(date, 'd MMM yyyy', { locale: pl });
    }
  };

  const handleBulkArchive = async () => {
    try {
      await Promise.all(selectedMessages.map(id => messagesApi.archive(id)));
      setSelectedMessages([]);
      loadMessages();
    } catch (error) {
      console.error('Error archiving messages:', error);
      alert('Błąd podczas archiwizacji wiadomości');
    }
  };

  const handleBulkDelete = async () => {
    if (confirm(`Czy na pewno chcesz usunąć ${selectedMessages.length} wiadomości?`)) {
      try {
        await Promise.all(selectedMessages.map(id => messagesApi.delete(id)));
        setSelectedMessages([]);
        loadMessages();
      } catch (error) {
        console.error('Error deleting messages:', error);
        alert('Błąd podczas usuwania wiadomości');
      }
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-pp-dark">
            {folderNames[folder] || folder}
          </h1>
          <span className="text-sm text-gray-500">
            {messages.length} wiadomości
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button 
            onClick={loadMessages}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Odśwież"
          >
            <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
          </button>
          
          {selectedMessages.length > 0 && (
            <>
              <button 
                onClick={handleBulkArchive}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors" 
                title="Archiwizuj zaznaczone"
              >
                <Archive size={20} />
              </button>
              <button 
                onClick={handleBulkDelete}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-red-500" 
                title="Usuń zaznaczone"
              >
                <Trash2 size={20} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Select all bar */}
      {messages.length > 0 && (
        <div className="bg-gray-50 border-b border-gray-200 px-4 py-2 flex items-center gap-4">
          <button 
            onClick={toggleSelectAll}
            className="p-1 hover:bg-gray-200 rounded"
          >
            {selectedMessages.length === messages.length ? (
              <CheckSquare size={20} className="text-pp-red" />
            ) : (
              <Square size={20} className="text-gray-400" />
            )}
          </button>
          <span className="text-sm text-gray-500">
            {selectedMessages.length > 0 
              ? `Zaznaczono ${selectedMessages.length}`
              : 'Zaznacz wszystkie'
            }
          </span>
        </div>
      )}

      {/* Messages list */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pp-red"></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <Mail size={48} className="mb-4 text-gray-300" />
            <p>Brak wiadomości w tym folderze</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {messages.map((message) => {
              const isUnread = message.status === 'RECEIVED';
              const isSelected = selectedMessages.includes(message.id);
              
              return (
                <div
                  key={message.id}
                  className={`
                    flex items-center gap-4 px-4 py-3 hover:bg-gray-50 cursor-pointer
                    transition-colors group
                    ${isUnread ? 'bg-blue-50/50' : ''}
                    ${isSelected ? 'bg-pp-red/5' : ''}
                  `}
                >
                  {/* Checkbox */}
                  <button 
                    onClick={(e) => { e.stopPropagation(); toggleSelect(message.id); }}
                    className="p-1 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    {isSelected ? (
                      <CheckSquare size={20} className="text-pp-red" />
                    ) : (
                      <Square size={20} className="text-gray-400" />
                    )}
                  </button>

                  {/* Star */}
                  <button className="p-1 hover:bg-gray-200 rounded">
                    <Star size={18} className="text-gray-300 hover:text-yellow-400" />
                  </button>

                  {/* Message icon */}
                  <div className={`${isUnread ? 'text-pp-red' : 'text-gray-400'}`}>
                    {isUnread ? <Mail size={20} /> : <MailOpen size={20} />}
                  </div>

                  {/* Message content - clickable */}
                  <Link 
                    to={`/message/${message.id}`}
                    className="flex-1 min-w-0 flex items-center gap-4"
                  >
                    {/* Sender */}
                    <div className={`w-48 truncate ${isUnread ? 'font-semibold' : ''}`}>
                      {message.sender?.name || message.sender?.address || 'Nieznany nadawca'}
                    </div>

                    {/* Subject & preview */}
                    <div className="flex-1 min-w-0">
                      <span className={`${isUnread ? 'font-semibold' : ''}`}>
                        {message.subject}
                      </span>
                      {message.content && (
                        <span className="text-gray-500 ml-2">
                          - {message.content.substring(0, 60)}...
                        </span>
                      )}
                    </div>

                    {/* Attachment indicator */}
                    {message.attachments?.length > 0 && (
                      <Paperclip size={16} className="text-gray-400 flex-shrink-0" />
                    )}

                    {/* Status badge */}
                    <span className={`
                      px-2 py-0.5 text-xs rounded-full flex-shrink-0
                      ${message.status === 'RECEIVED' ? 'bg-blue-100 text-blue-700' : ''}
                      ${message.status === 'READ' ? 'bg-gray-100 text-gray-600' : ''}
                      ${message.status === 'SENT' ? 'bg-green-100 text-green-700' : ''}
                      ${message.status === 'OPENED' ? 'bg-purple-100 text-purple-700' : ''}
                    `}>
                      {statusLabels[message.status] || message.status}
                    </span>

                    {/* Date */}
                    <span className="text-sm text-gray-500 w-24 text-right flex-shrink-0">
                      {formatDate(message.receivedAt || message.sentAt)}
                    </span>
                  </Link>

                  {/* More actions */}
                  <button className="p-1 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                    <MoreVertical size={18} className="text-gray-400" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      {messages.length > 0 && (
        <div className="bg-white border-t border-gray-200 px-4 py-3 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Wyświetlono 1-{messages.length} z {messages.length}
          </span>
          <div className="flex items-center gap-2">
            <button className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50" disabled>
              <ChevronLeft size={20} />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50" disabled>
              <ChevronRight size={20} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

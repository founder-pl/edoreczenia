import { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  CheckCircle, ArrowRight, ExternalLink, Copy, Check,
  User, Shield, Mail, FileText, Building, CreditCard
} from 'lucide-react';

const steps = [
  {
    id: 1,
    title: 'Zaloguj się do Panelu Certum',
    description: 'Wejdź na stronę Certum i zaloguj się. Jeśli nie masz jeszcze konta, załóż je podając swój adres e-mail.',
    icon: User,
    action: {
      label: 'Otwórz Panel Certum',
      url: 'https://panel.certum.pl/'
    },
    tips: [
      'Użyj aktualnego adresu e-mail',
      'Zapamiętaj hasło lub użyj menedżera haseł',
      'Potwierdź rejestrację klikając link w e-mailu'
    ]
  },
  {
    id: 2,
    title: 'Wybierz metodę uwierzytelnienia',
    description: 'Z dostępnych metod wybierz sposób uwierzytelnienia skrzynki: mObywatel lub podpis elektroniczny Certum.',
    icon: Shield,
    tips: [
      'mObywatel - najszybsza metoda dla osób fizycznych',
      'Podpis elektroniczny - dla firm i zaawansowanych użytkowników',
      'Obie metody są bezpieczne i zgodne z przepisami'
    ]
  },
  {
    id: 3,
    title: 'Wybierz skrzynkę w wersji Free',
    description: 'Wybierz darmową wersję skrzynki e-Doręczeń. Możesz później przejść na wersję płatną.',
    icon: CreditCard,
    highlight: true,
    tips: [
      'Wersja Free jest bezpłatna',
      'Zawiera wszystkie podstawowe funkcje',
      'Idealna do rozpoczęcia pracy z e-Doręczeniami'
    ]
  },
  {
    id: 4,
    title: 'Uzupełnij dane wnioskodawcy',
    description: 'Wybierz typ skrzynki (firma, osoba prywatna) i uzupełnij wniosek swoimi danymi: PESEL, NIP lub KRS.',
    icon: FileText,
    fields: [
      { num: '1', label: 'Prefiks kraju (+48)' },
      { num: '2', label: 'Numer telefonu' },
      { num: '3', label: 'Imię i nazwisko' },
      { num: '4', label: 'Kraj' },
      { num: '5', label: 'Województwo' },
      { num: '6', label: 'Kod pocztowy' },
      { num: '7', label: 'Miejscowość' },
      { num: '8', label: 'Ulica' },
      { num: '9', label: 'Numer domu' },
      { num: '10', label: 'Numer lokalu' },
    ],
    tips: [
      'Wszystkie pola z gwiazdką (*) są obowiązkowe',
      'Dane muszą być zgodne z dokumentem tożsamości',
      'Dla firm podaj dane z KRS/CEIDG'
    ]
  },
  {
    id: 5,
    title: 'Wprowadź kod polecający',
    description: 'W polu "Partner, który polecił Ci skrzynkę e-Doręczeń" (pole 11) wprowadź nasz kod polecający.',
    icon: Mail,
    highlight: true,
    referralCode: 'skrzynka@edoreczenia.pl',
    tips: [
      'Kod daje dostęp do bezpłatnej skrzynki',
      'Pole znajduje się na dole formularza',
      'Skopiuj kod klikając przycisk obok'
    ]
  },
  {
    id: 6,
    title: 'Gotowe! Zacznij korzystać',
    description: 'Po zatwierdzeniu wniosku otrzymasz adres ADE i możesz zacząć korzystać z e-Doręczeń.',
    icon: CheckCircle,
    action: {
      label: 'Przejdź do skrzynki',
      url: '/inbox',
      internal: true
    },
    tips: [
      'Adres ADE otrzymasz na e-mail',
      'Możesz go użyć w naszym panelu SaaS',
      'Skonfiguruj integracje w Ustawieniach'
    ]
  }
];

export default function GuidePage() {
  const [completedSteps, setCompletedSteps] = useState([]);
  const [copiedCode, setCopiedCode] = useState(false);

  const toggleStep = (stepId) => {
    setCompletedSteps(prev => 
      prev.includes(stepId) 
        ? prev.filter(id => id !== stepId)
        : [...prev, stepId]
    );
  };

  const copyReferralCode = (code) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero section */}
      <div className="gradient-dark text-white py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 rounded-full text-sm mb-6">
            <Mail size={16} />
            <span>Przewodnik krok po kroku</span>
          </div>
          <h1 className="text-4xl font-bold mb-4">
            Załóż skrzynkę <span className="text-pp-red">e-Doręczeń</span> w kilka minut
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Dowiedz się, jak założyć skrzynkę e-Doręczeń Certum i rozpocząć 
            elektroniczną komunikację z urzędami.
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Postęp: {completedSteps.length} z {steps.length} kroków
            </span>
            <span className="text-sm text-gray-500">
              {Math.round((completedSteps.length / steps.length) * 100)}%
            </span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-pp-red transition-all duration-500"
              style={{ width: `${(completedSteps.length / steps.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="space-y-8">
          {steps.map((step, index) => {
            const isCompleted = completedSteps.includes(step.id);
            const Icon = step.icon;
            
            return (
              <div 
                key={step.id}
                className={`
                  card p-6 transition-all duration-300
                  ${step.highlight ? 'ring-2 ring-pp-red ring-offset-2' : ''}
                  ${isCompleted ? 'bg-green-50 border-green-200' : ''}
                `}
              >
                <div className="flex gap-6">
                  {/* Step number */}
                  <div className="flex-shrink-0">
                    <button
                      onClick={() => toggleStep(step.id)}
                      className={`
                        w-12 h-12 rounded-full flex items-center justify-center
                        transition-all duration-300 cursor-pointer
                        ${isCompleted 
                          ? 'bg-green-500 text-white' 
                          : 'bg-pp-dark text-white hover:bg-pp-red'
                        }
                      `}
                    >
                      {isCompleted ? (
                        <Check size={24} />
                      ) : (
                        <span className="text-lg font-bold">{step.id}</span>
                      )}
                    </button>
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-xl font-semibold text-pp-dark flex items-center gap-2">
                          <Icon size={20} className="text-pp-red" />
                          {step.title}
                        </h3>
                        <p className="text-gray-600 mt-1">{step.description}</p>
                      </div>
                    </div>

                    {/* Referral code */}
                    {step.referralCode && (
                      <div className="my-4 p-4 bg-pp-red/10 rounded-xl border-2 border-dashed border-pp-red">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-pp-red font-medium mb-1">
                              Kod polecający (pole 11):
                            </p>
                            <p className="text-2xl font-bold text-pp-dark font-mono">
                              {step.referralCode}
                            </p>
                          </div>
                          <button
                            onClick={() => copyReferralCode(step.referralCode)}
                            className={`
                              flex items-center gap-2 px-4 py-2 rounded-lg transition-all
                              ${copiedCode 
                                ? 'bg-green-500 text-white' 
                                : 'bg-pp-red text-white hover:bg-red-700'
                              }
                            `}
                          >
                            {copiedCode ? (
                              <>
                                <Check size={18} />
                                <span>Skopiowano!</span>
                              </>
                            ) : (
                              <>
                                <Copy size={18} />
                                <span>Kopiuj</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Form fields reference */}
                    {step.fields && (
                      <div className="my-4 p-4 bg-gray-50 rounded-xl">
                        <p className="text-sm font-medium text-gray-700 mb-3">
                          Pola formularza:
                        </p>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                          {step.fields.map((field) => (
                            <div 
                              key={field.num}
                              className="flex items-center gap-2 text-sm"
                            >
                              <span className="w-6 h-6 bg-pp-dark text-white rounded-full flex items-center justify-center text-xs font-bold">
                                {field.num}
                              </span>
                              <span className="text-gray-600 truncate">{field.label}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Tips */}
                    {step.tips && (
                      <div className="mt-4">
                        <ul className="space-y-2">
                          {step.tips.map((tip, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                              <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                              <span>{tip}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Action button */}
                    {step.action && (
                      <div className="mt-4">
                        {step.action.internal ? (
                          <Link
                            to={step.action.url}
                            className="inline-flex items-center gap-2 btn-primary"
                          >
                            {step.action.label}
                            <ArrowRight size={18} />
                          </Link>
                        ) : (
                          <a
                            href={step.action.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 btn-primary"
                          >
                            {step.action.label}
                            <ExternalLink size={18} />
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Completion message */}
        {completedSteps.length === steps.length && (
          <div className="mt-12 p-8 bg-green-50 rounded-2xl border border-green-200 text-center animate-fadeIn">
            <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={32} className="text-white" />
            </div>
            <h3 className="text-2xl font-bold text-green-800 mb-2">
              Gratulacje! 🎉
            </h3>
            <p className="text-green-700 mb-6">
              Ukończyłeś wszystkie kroki. Twoja skrzynka e-Doręczeń jest gotowa do użycia!
            </p>
            <Link to="/inbox" className="btn-primary">
              Przejdź do skrzynki
            </Link>
          </div>
        )}

        {/* Help section */}
        <div className="mt-12 p-6 bg-blue-50 rounded-2xl">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">
            Potrzebujesz pomocy?
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a 
              href="https://edoreczenia.poczta-polska.pl/informacje/faq/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-white rounded-xl hover:shadow-md transition-shadow"
            >
              <FileText size={24} className="text-blue-600" />
              <div>
                <div className="font-medium text-gray-900">FAQ</div>
                <div className="text-sm text-gray-500">Najczęściej zadawane pytania</div>
              </div>
            </a>
            <a 
              href="https://www.youtube.com/watch?v=ACO5lwOlQUw"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-white rounded-xl hover:shadow-md transition-shadow"
            >
              <Building size={24} className="text-blue-600" />
              <div>
                <div className="font-medium text-gray-900">Wideo poradnik</div>
                <div className="text-sm text-gray-500">Jak aktywować e-Polecony</div>
              </div>
            </a>
            <Link 
              to="/settings"
              className="flex items-center gap-3 p-4 bg-white rounded-xl hover:shadow-md transition-shadow"
            >
              <Shield size={24} className="text-blue-600" />
              <div>
                <div className="font-medium text-gray-900">Ustawienia</div>
                <div className="text-sm text-gray-500">Konfiguracja integracji</div>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

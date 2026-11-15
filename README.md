# Kartoteka pojazdów dla Home Assistant

Kartoteka samochodów w Home Assistant: badanie techniczne, OC/AC, przeglądy serwisowe, elementy eksploatacyjne i inne terminy – z przypomnieniami, kalendarzem i przyciskami „zrobione”.

Każde auto to osobne urządzenie. Integracja niczego nie pobiera z internetu – wszystkie dane wpisujesz sam w formularzu.

## Co daje

- **Dane auta** – nazwa, numer rejestracyjny, marka, model, rocznik, VIN, paliwo, przebieg, notatki.
- **Terminy z datą** – badanie techniczne, koniec OC (z ubezpieczycielem i numerem polisy), koniec AC, kolejny przegląd serwisowy.
- **Przegląd wg producenta** – co ile miesięcy i co ile km; liczy się to, co nastąpi pierwsze. Sensor „Km do przeglądu”.
- **Eksploatacja** – rozrząd, płyn hamulcowy, filtr kabinowy, akumulator, każdy z własnym interwałem czasu i/lub kilometrów.
- **Dodatkowe daty** – koniec gwarancji, assistance, leasingu, winiety CZ / AT / SK.
- **Najbliższy termin** – sensor z datą i listą wszystkich terminów w atrybutach.
- **Wymaga uwagi** – binary sensor włączany, gdy do terminu zostało mniej niż ustawiona liczba dni lub km (domyślnie 30 dni / 1000 km).
- **Kalendarz** – wszystkie terminy w zakładce Kalendarz.
- **Przebieg** – encja liczbowa do wpisania z dashboardu lub automatyzacji.
- **Przyciski** – „Przegląd wykonany”, „Badanie wykonane”, „Odnów OC”, „Odnów AC” i „Wymieniono” dla elementów eksploatacyjnych. Same wyliczają kolejne daty.

## Instalacja

1. Ustawienia → **Marketplace** → **Dodaj z linku** → `bepropl/ha-kartoteka-pojazdow` (typ: Integracja).
2. Zainstaluj **Kartoteka pojazdów** i uruchom ponownie Home Assistant.
3. Ustawienia → Urządzenia i usługi → **Dodaj integrację** → **Kartoteka pojazdów**.

Każdy samochód dodajesz osobno (kolejne „Dodaj wpis”). Numer rejestracyjny musi być unikalny.

## Edycja

Ustawienia → Urządzenia i usługi → Kartoteka pojazdów → **Konfiguruj** przy aucie. Menu:

| Pozycja | Co zmienia |
|---|---|
| Dane auta | nazwa, rejestracja, marka, model, VIN, przebieg, notatki |
| Badanie, ubezpieczenie i przegląd | daty, interwały, progi ostrzeżeń |
| Eksploatacja | rozrząd, płyn hamulcowy, filtr kabinowy, akumulator |
| Gwarancja, assistance, leasing, winiety | daty końca |

Element eksploatacyjny włącza się, gdy podasz datę lub przebieg ostatniej wymiany.

## Jak liczone są terminy

- **Badanie wykonane** – następne badanie = dziś + interwał badania (domyślnie 12 mies.).
- **Przegląd wykonany** – zapisuje dzisiejszą datę i aktualny przebieg jako ostatni przegląd.
- **Odnów OC / AC** – przedłuża polisę o 12 miesięcy od końca obecnej (a jeśli już wygasła – od dziś).
- Dodawanie miesięcy przycina dzień do końca miesiąca (31.01 + 1 mies. = 28/29.02).
- Liczba dni do terminu odświeża się codziennie o północy.

## Przykład: powiadomienie

```yaml
alias: Auto wymaga uwagi
triggers:
  - trigger: state
    entity_id: binary_sensor.rodzinne_kombi_kr12345_wymaga_uwagi
    to: "on"
actions:
  - action: notify.mobile_app_telefon
    data:
      title: "🚗 {{ state_attr(trigger.entity_id, 'plate') }}"
      message: >-
        {% for i in state_attr(trigger.entity_id, 'issues') %}
        {{ i.kind }}: {{ i.days_left ~ ' dni' if i.days_left is defined else i.km_left ~ ' km' }}
        {% endfor %}
```

## Przykład: przebieg z integracji auta

Jeśli auto ma własną integrację w HA, przebieg można kopiować automatycznie:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.moje_auto_odometer
actions:
  - action: number.set_value
    target:
      entity_id: number.rodzinne_kombi_kr12345_przebieg
    data:
      value: "{{ trigger.to_state.state | int }}"
```

Nazwy encji zależą od nazwy auta i języka – sprawdź je na stronie urządzenia.

## Licencja

MIT

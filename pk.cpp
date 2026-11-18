#include <iostream>
#include <memory>
#include <string>
#include <windows.h>
#include <algorithm>
#include <vector>

using namespace std;

//Адаптер
class Logger {
public:
    virtual void log(const string& message) = 0;
    virtual ~Logger() = default;
};

class ConsoleLogger : public Logger {
public:
    void log(const string& message) override {
        cout << "[LOG] " << message << "\n";
    }
};

class OldFileWriter {
public:
    void writeLine(const char* text) {
        cout << "OldFileWriter " << text << "\n";
    }
};

class FileWriterAdapter : public Logger {
public:
    FileWriterAdapter(OldFileWriter& w) : writer(w) {}
    void log(const string& message) override {
        writer.writeLine(message.c_str());
    }
private:
    OldFileWriter& writer;   // адаптируемый объект (композиция)
};

void runApp(Logger& logger) {
    logger.log("Программа запущена");
    logger.log("Данные сохранены");
}

int main() {
    SetConsoleOutputCP(65001);
    SetConsoleCP(65001);
    ConsoleLogger console;
    runApp(console);
    OldFileWriter oldWriter;
    FileWriterAdapter adapter(oldWriter);
    runApp(adapter);
    return 0;
}

//Фабричный метод
// class Transport {
// public:
//     virtual void deliver(const string& cargo) const = 0;
//     virtual ~Transport() = default;
// };

// class Truck : public Transport {
// public:
//     void deliver(const string& cargo) const override {
//         cout << "Грузовик везёт по дороге: " << cargo << "\n";
//     }
// };

// class Ship : public Transport {
// public:
//     void deliver(const string& cargo) const override {
//         cout << "Корабль везёт по морю: " << cargo << "\n";
//     }
// };

// class Logistics {
// public:
//     virtual ~Logistics() = default;
//     virtual unique_ptr<Transport> createTransport() const = 0;
//     void planDelivery(const string& cargo) const {
//         createTransport()->deliver(cargo);
//     }
// };

// class RoadLogistics : public Logistics {
// public:
//     unique_ptr<Transport> createTransport() const override {
//         return make_unique<Truck>();
//     }
// };

// class SeaLogistics : public Logistics {
// public:
//     unique_ptr<Transport> createTransport() const override {
//     return make_unique<Ship>();
//     }
// };

// int main() {
//     SetConsoleOutputCP(65001);
//     SetConsoleCP(65001);
//     unique_ptr<Logistics> logistics;
//     logistics = make_unique<RoadLogistics>();
//     logistics->planDelivery("10 тонн яблок");
//     logistics = make_unique<SeaLogistics>();
//     logistics->planDelivery("контейнер с электроникой");
//     return 0;
// }


//Наблюдатель
// class Observer {
// public:
//     virtual void update(double temperature) = 0;
//     virtual ~Observer() = default;
// };

// class WeatherStation {
// public:
//     void subscribe(Observer* o) { observers_.push_back(o); }
//     void unsubscribe(Observer* o) {
//         observers_.erase(remove(observers_.begin(), observers_.end(), o),
//                          observers_.end());
//     }
//     void setTemperature(double t) {
//         cout << "Станция: новая температура " << t << "\n";
//         temperature_ = t;
//         notify();
//     }
// private:
//     void notify() {
//         for (Observer* o : observers_) o->update(temperature_);
//     }
//     vector<Observer*> observers_;
//     double temperature_ = 0;
// };

// class PhoneDisplay : public Observer {
// public:
//     void update(double t) override {
//         cout << "  Телефон: сейчас " << t << " °C\n";
//     }
// };

// class HeaterController : public Observer {
// public:
//     void update(double t) override {
//         cout << "  Обогреватель: " << (t < 18 ? "включаюсь" : "выключен") << "\n";
//     }
// };

// int main() {
//     SetConsoleOutputCP(65001);
//     SetConsoleCP(65001);

//     WeatherStation station;
//     PhoneDisplay phone;
//     HeaterController heater;

//     station.subscribe(&phone);
//     station.subscribe(&heater);
//     station.setTemperature(15);
//     station.setTemperature(22);
//     station.unsubscribe(&heater);   
//     station.setTemperature(10);

//     return 0;
// }
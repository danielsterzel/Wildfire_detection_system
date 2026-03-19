import { useState } from "react";
import { useEffect } from "react";

export function Dashboard() {
  const [currentSection, setCurrentSection] = useState("homeSection");
  const [showFunctionalSection, setShowFunctionalSection] = useState(false);

  const [temp, setTemp] = useState(0);
  const [humidity, setHumidity] = useState(0);
  const [windSpeed, setWindSpeed] = useState(0);
  const [windDirection, setWindDirection] = useState("");
  const [solarRadiation, setSolarRadiation] = useState(0);
  const [particleConcentration, setParticleConcentration] = useState(0);
  const [humanActivity, setHumanActivity] = useState(0);


  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        setCurrentSection((prevState) => {
          if (prevState !== "homeSection") {
            return prevState;
          }
          setShowFunctionalSection(true);

          return "functionalSection";
        });
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div>
      <div
        className="h-[85vh] w-screen relative bg-cover bg-center"
        style={{ backgroundImage: "url('/forest.jpg')" }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/30 to-black/95" />
        <div className="absolute inset-0 backdrop-blur-[0.3px]" />
        <div className="absolute inset-0 h-full flex justify-center items-center">
          <div
            className={`flex flex-col justify-start items-center px-12 py-10 
            rounded-2xl bg-white backdrop-blur-md -mt-[20vh]
            border-2 border-teal-500
        ${currentSection === "functionalSection" && "animate-fadeOutUp"}`}
          >
            <h1
              className={`text-4xl w-fit transition-all duration-700 ease-out
            ${currentSection === "homeSection" && "animate-fadeDown"}
            `}
            >
              Wildfire Detection System
            </h1>
            <p
              className={`pt-8 w-fit transition-all duration-700 ease-out text-xl text-gray-600 
            ${currentSection === "homeSection" && "animate-fadeUp"}`}
            >
              Press Enter to begin
            </p>
          </div>
        </div>
      </div>
      {showFunctionalSection && (
        <div
          className={`absolute inset-0 h-[100vh] grid grid-cols-4 px-12 py-24 gap-4 h-screen
        ${currentSection === "functionalSection" && "opacity-0 animate-gridFadeUp"}
      `}
        >
          <div className="bg-white rounded-xl flex flex-col items-center py-4 px-4 justify-start">
            <p className="border-b border-black text-center mx-auto max-w-md font-bold">«Environmental parameters»</p>
            <div className="py-8 px-4">
                <ul className="flex flex-col gap-4 justify-center max-w-xs mx-auto">
                    <li>
                        <div className="flex items-center gap-4">
                        <i className="fa-solid fa-temperature-half fa-fw text-lg"></i>Temperature: {temp}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-4">
                        <i className="fa-solid fa-droplet fa-fw text-lg"></i>Humidity: {humidity}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-4">
                            <i className="fa-solid fa-gauge-high fa-fw text-lg"></i>Wind speed: {windSpeed}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-4">
                            <i className="fa-solid fa-wind fa-fw text-lg"></i>Wind direction: {windDirection}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-4">
                            <i className="fa-solid fa-cloud-sun fa-fw text-lg"></i>Solar Radiation: {solarRadiation} {/*[W/m²]*/}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-4">
                        <i className="fa-solid fa-smog fa-fw text-lg"></i>Gas and particulate concentration: {particleConcentration}{/*µg/m³*/}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-4">
                            <i className="fa-solid fa-people-group fa-fw text-lg"></i>Human Activity Index: {humanActivity}
                        </div>
                    </li>
                </ul>
            </div>
          </div>
          <div className="col-span-2 bg-white rounded-xl flex flex-col py-4 px-4 items-center justify-start">
            <p className="border-b border-black text-center mx-auto max-w-md font-bold">¯\_(ツ)_/¯ ForestGrid ¯\_(ツ)_/¯</p>
          </div>
          <div className="bg-white rounded-xl flex flex-col items-center py-4 px-4 justify-start">
            <p className="border-b border-black text-center mx-auto max-w-md font-bold">Output modelu maybe? 💯💯💯💯💯💯💯💯💯💯💯💯💯💯</p>
          </div>
        </div>
      )}
      <div className="w-full h-[15vh] bg-black"></div>
    </div>
  );
}

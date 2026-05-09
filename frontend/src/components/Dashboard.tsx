import { useState } from "react";
import { useEffect } from "react";
import { Grid } from "./Grid";

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
          className={`relative w-full min-h-screen grid grid-cols-12 px-4 py-8 gap-2 bg-gray-950 auto-rows-max
        ${currentSection === "functionalSection" && "opacity-0 animate-gridFadeUp"}
      `}
        >
          <div className="col-span-2 bg-white rounded-xl flex flex-col items-center py-3 px-3 justify-start overflow-y-auto h-fit">
            <p className="border-b border-black text-center mx-auto max-w-md font-bold text-sm">«Environmental parameters»</p>
            <div className="py-4 px-2">
                <ul className="flex flex-col gap-2 justify-center max-w-xs mx-auto text-xs">
                    <li>
                        <div className="flex items-center gap-2">
                        <i className="fa-solid fa-temperature-half fa-fw text-sm"></i>Temperature: {temp}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-2">
                        <i className="fa-solid fa-droplet fa-fw text-sm"></i>Humidity: {humidity}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-2">
                            <i className="fa-solid fa-gauge-high fa-fw text-sm"></i>Wind speed: {windSpeed}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-2">
                            <i className="fa-solid fa-wind fa-fw text-sm"></i>Wind direction: {windDirection}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-2">
                            <i className="fa-solid fa-cloud-sun fa-fw text-sm"></i>Solar Radiation: {solarRadiation}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-2">
                        <i className="fa-solid fa-smog fa-fw text-sm"></i>Particulate: {particleConcentration}
                        </div>
                    </li>
                    <li>
                        <div className="flex items-center gap-2">
                            <i className="fa-solid fa-people-group fa-fw text-sm"></i>Human Activity: {humanActivity}
                        </div>
                    </li>
                </ul>
            </div>
          </div>
          <div className="col-span-8 h-fit">
            <Grid />
          </div>
          <div className="col-span-2 bg-white rounded-xl flex flex-col items-center py-3 px-3 justify-start h-fit">
            <p className="border-b border-black text-center mx-auto max-w-md font-bold text-sm">Statistics</p>
            <div className="py-4 px-2">
              <p className="text-xs text-gray-600">Simulation metrics will appear here</p>
            </div>
          </div>
        </div>
      )}
      <div className="w-full h-[15vh] bg-black"></div>
    </div>
  );
}

## Skriftlig rapport

## Syfte
Jag ville initialt se om jag kunde sammanfatta vad varje kommunpolitiker röstade på för varje motion som det röstades om i Malmö kommun under förra mandadarperioden för att få en inblick i vad som faktiskt bestäms av politikerna i min kommun. Men jag insåg ganska snabbt att detta skulle bli mycket omfattande då det dels inte alltid finns en tydlig lista på vad varje politiker har röstat ja eller nej på (Ibland så röstar de enbart genom handuppräckning utan att det dokumenteras) och dels för att vissa omröstningar bara handlar om en motion ska skickas vidare för granskning av olika nämnder eller inte för att sedan eventuellt röstas om igen efter att diverse nämnder gett sin rekommendation om förslaget. Jag bestämde mig därför att enbart mäta närvaro för varje förtroendevald politiker i kommunfullmäktige för att få en uppfaattning om hur delaktiga de faktiskt är i det som bestäms i politiken. Detta visade sig vara mer omfattande än jag först trodde. 

## Området och dess relevans
Jag valde området webscraping, men projektets huvudsakliga problemlösning kom att handla mer om pdf-avläsning och regex logik än något annat.
Onmrådet är relevant eftersom jag behandlar olika typer av data (pdf, json) och försöker sammanfatta det visuellt med matplotlib.

## Viktiga begrepp
Det finns egentligen inga specifika tekniska begrepp att förklara. De bergrepp som behövs förklaras är i så fall de politiska begreppen.


## Genomförande
Jag började med att koda grunderna i en notebook för att få en förståelse för de nya biblioteken jag använde. De nya biblioteken är Beautiful Soup som jag använde för att klättra i mötes-trädet på hemsidan för att kunna ladda ner ett möteprotokoll med närvorlista för varje möte. Det andra nya biblioteket är pdf-plumber som jag använde för att läsa av pdferna till tex för att kunna extrahera informationen.
Lösningen fungerar genom att jag först hämtar varje politker från malmöstads hemsida med beautiful soup genom ett api-anrop som returnerar ett json objkekt med alla politker. Sedan går jag in på varje möteslänk med beautiful soup och hämtar länkarna till varje pdf-fil som beskriver varje möte. Däefter öppnar jag varje pdf-fil med pdf-plumber och extraherar varje politkers närvaro och om de har blivit ersatta av någon annan. För varje möte står det på vilka paragrafer en politker varit närvarnde och på vilka paragrafer den varit ersatt. jag kan därför utläsa närvaro för varje punkt som det beslutats om vilket innebär att jag även får information om en politker enbart har varit delvis närvarande. Men här kom också utmaningen med projektet då syntaxen för hur närvaron skrevs i pdferna inte alltid var likadan. Vissa poliker var med på vissa paragrafer i början och vissa paragrafer i slutet av mötet. Vissa politker var med på vissa delpunkter av en paragraf vilket jag gjorde om till att polikern skulle räknas som närvarnde under hela paragrafen. Vissa täcken som - och dubbell -- gjorde att inläsningen misslyckades. Jag löste detta genom att lösa ett fel i taget och köra om priogrammet många gånger tills nöstan alla pdfer passerade. 

## Resultat
Lösningen sammanställer närvaron på politikerna i kommunfullmäktige genom graferna i data/plots.
Den ger:
Närvaro per paragraf per politker
Genomsnittlig närvaror per paragraf per parti
Närvaro per möte (närvarande på mins en paragraf räknas som full närvaro) per politker
Genomsnittlig närvaror möte (närvarande på mins en paragraf räknas som full närvaro) per parti
Se under data/plots

## Begränsningar och möjliga förbättringar
1. Ibland deltar inte en politiker på en viss paragraf pga "jäv". Jäv betyder att en politiker upplever att denna inte kan vara opartisk i beslutet pga t.ex. finansiella intressen eller andra intressen. Detta räknas just nu som fullständig frånvaro trots att polikern gjort rätt ifrån sig genom att avstå. För att kunna fånga upp detta så behöver man läsa igenom vgarje paragraf i hela pdfen. Just nu läser jag bara av närvarolistan högst upp i pdf:en. 

2. Ibland är politiker frånvarande på bara vissa delpunkter av en paragraf pga jäv. Idag räknas det som att politikern är närvarnade under hela paragrafen vilken inte ger en riktigt så detaljerad bild av verkligheten som det skulle kunna göra.

3. Just nu delar jag upp närvarolistan med hjälp av re-syntax. Detta gör att jag måste skriva många versioner av en syntax eftersom det fanns många versioner av en syntax där t.ex. felstavningar eller extra komman eller liknande kan finnas med. En mer robust lösning skulle kunna vara att mashinelearning känner igen syntaxen istället så att programmet inte kraschar vid nya inläsningar och eventullt nya syntaxer och stavfel.

## Koppling till yrkesrollen
Både Beautiful soup och pdf-plumber kan vara mycket användbara inom data-science. Mycket av datan vi vill åt finns online och då är beautifulsoup ett utmärkt verktyg. Pdf-plumber var också mycket användbart till att extrahera information från pdf-erna.

## Källor
Ange de viktigaste källorna och dokumentationen du har använt.
Regex: https://www.youtube.com/watch?v=K8L6KVGG-7o&t=1928s
Beautiful soup: https://beautiful-soup-4.readthedocs.io/en/latest/, https://www.youtube.com/watch?v=ng2o98k983k
Pdf plumber: chat gpt


## Självreflektion
- Vad lärde du dig som du inte kunde innan?
Jag lärde mig att hämta data från en hemsida och klättra på en hemnsida med Beautiful Soup och att läsa av pdf-er med pdf-plumvber samt att kunna använda regex för syntaxlogik.

- Vad var svårast att förstå eller genomföra?
Att använda logik med Regex för att skapa regler för avläsning av närvaron. Men även att lista ut på vilket sätt man borde spara informationen. Man skulle kunna spara en csv per möte. eller att en rad var en poliker och att man hade flera kolumner för varje paragraf.

- Vilket tekniskt val är du mest nöjd med och varför?
Att dela upp pdf-raderna i ett förutsägbart mönster. T.ex. så vet jag att varje rad bröjar med en politiker och (parti). Jag skrev därför en funktion som delade upp raden med partimedlemmen och sedan rautnerade jag resten av raden
för vidare behandling. Detta hjälpte mig att inte bahandla all logik på en och samma gång.

- Vad hade du gjort annorlunda om du började om?
Jag hade försökt bryta ner logiken i ännu mindre bitar och struntat i refaktoring då det tog en hel del tid från logikbyggandet.

- Vad skulle vara ett naturligt nästa steg om du fortsatte arbetet?
Att använda AI/mashine learning för känna igen syntaxen av raderna istället för Regex.

- Vilket betyg tycker du själv att arbetet motsvarar – G eller VG?
G

- Motivera din bedömning genom att koppla till kraven för G och VG nedan.
Jag borde valt ett ännu smalare område .tex. enbart webscarping för att fullt ut lära mig det biblioteket. Eftersom jag inte gjorde lärde jag mig lite mindre ljupgående om just webscraping men mer överskådlig förståelse av webscraping, pdf-avläsning och regex.

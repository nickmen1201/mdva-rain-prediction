--
-- PostgreSQL database dump
--

\restrict iFrNTyez58Ft68GRqRfrwmzPofRGXD44H8DpppDiyohdBygqrXaeCCRbr4o8RbK

-- Dumped from database version 18.2
-- Dumped by pg_dump version 18.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: camiloardila; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA camiloardila;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: barrios; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.barrios (
    id_barrio character varying(20) NOT NULL,
    nombre character varying(255) NOT NULL,
    id_comuna character varying(20) NOT NULL
);


--
-- Name: comunas; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.comunas (
    id_comuna character varying(20) NOT NULL,
    nombre character varying(255) NOT NULL,
    id_municipio character varying(20) NOT NULL
);


--
-- Name: municipios; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.municipios (
    id_municipio character varying(20) NOT NULL,
    nombre character varying(255) NOT NULL
);


--
-- Name: tipos_motor; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.tipos_motor (
    id_motorizacion smallint NOT NULL,
    nombre character varying(100) NOT NULL
);


--
-- Name: tipos_motor_id_motorizacion_seq; Type: SEQUENCE; Schema: camiloardila; Owner: -
--

CREATE SEQUENCE camiloardila.tipos_motor_id_motorizacion_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipos_motor_id_motorizacion_seq; Type: SEQUENCE OWNED BY; Schema: camiloardila; Owner: -
--

ALTER SEQUENCE camiloardila.tipos_motor_id_motorizacion_seq OWNED BY camiloardila.tipos_motor.id_motorizacion;


--
-- Name: tipos_vehiculo; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.tipos_vehiculo (
    id_tipo_vehiculo smallint NOT NULL,
    nombre character varying(100) NOT NULL,
    vulnerabilidad smallint NOT NULL,
    CONSTRAINT tipos_vehiculo_vulnerabilidad_check CHECK (((vulnerabilidad >= 0) AND (vulnerabilidad <= 100)))
);


--
-- Name: tipos_vehiculo_id_tipo_vehiculo_seq; Type: SEQUENCE; Schema: camiloardila; Owner: -
--

CREATE SEQUENCE camiloardila.tipos_vehiculo_id_tipo_vehiculo_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipos_vehiculo_id_tipo_vehiculo_seq; Type: SEQUENCE OWNED BY; Schema: camiloardila; Owner: -
--

ALTER SEQUENCE camiloardila.tipos_vehiculo_id_tipo_vehiculo_seq OWNED BY camiloardila.tipos_vehiculo.id_tipo_vehiculo;


--
-- Name: usuarios; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.usuarios (
    id bigint NOT NULL,
    nombre character varying(120) NOT NULL,
    username character varying(60) NOT NULL,
    email character varying(255) NOT NULL,
    fecha_nacimiento date,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    authhash character varying(255),
    id_barrio character varying(20) NOT NULL
);


--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: camiloardila; Owner: -
--

CREATE SEQUENCE camiloardila.usuarios_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: camiloardila; Owner: -
--

ALTER SEQUENCE camiloardila.usuarios_id_seq OWNED BY camiloardila.usuarios.id;


--
-- Name: vehiculos; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.vehiculos (
    placa character varying(10) NOT NULL,
    id_usuario integer NOT NULL,
    id_tipo_vehiculo smallint NOT NULL,
    id_motorizacion smallint NOT NULL,
    marca character varying(100) NOT NULL,
    modelo character varying(100) NOT NULL,
    ano smallint NOT NULL,
    CONSTRAINT vehiculos_ano_check CHECK (((ano >= 1900) AND ((ano)::numeric <= (EXTRACT(year FROM CURRENT_DATE) + (1)::numeric))))
);


--
-- Name: viajes; Type: TABLE; Schema: camiloardila; Owner: -
--

CREATE TABLE camiloardila.viajes (
    id_viaje integer NOT NULL,
    id_usuario integer NOT NULL,
    id_vehiculo integer,
    id_ubi_origen integer NOT NULL,
    id_ubi_destino integer NOT NULL,
    t_estimado smallint NOT NULL,
    h_inicio timestamp with time zone NOT NULL,
    h_fin timestamp with time zone,
    id_clima_inicio integer NOT NULL,
    id_clima_fin integer,
    precipitacion_mm smallint NOT NULL,
    finalizado boolean DEFAULT false NOT NULL,
    user_rating smallint
);


--
-- Name: tipos_motor id_motorizacion; Type: DEFAULT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.tipos_motor ALTER COLUMN id_motorizacion SET DEFAULT nextval('camiloardila.tipos_motor_id_motorizacion_seq'::regclass);


--
-- Name: tipos_vehiculo id_tipo_vehiculo; Type: DEFAULT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.tipos_vehiculo ALTER COLUMN id_tipo_vehiculo SET DEFAULT nextval('camiloardila.tipos_vehiculo_id_tipo_vehiculo_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.usuarios ALTER COLUMN id SET DEFAULT nextval('camiloardila.usuarios_id_seq'::regclass);


--
-- Data for Name: barrios; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.barrios (id_barrio, nombre, id_comuna) FROM stdin;
MED0101	Santo Domingo Savio No. 1	MED01
MED0102	Santo Domingo Savio No. 2	MED01
MED0103	Popular	MED01
MED0104	Granizal	MED01
MED0105	Moscu No. 2	MED01
MED0106	Villa de Guadalupe	MED01
MED0107	San Pablo	MED01
MED0108	El Compromiso	MED01
MED0109	Aldea Pablo VI	MED01
MED0110	La Esperanza No. 2	MED01
MED0111	La Avanzada	MED01
MED0112	Carpinelo	MED01
MED0201	La Isla	MED02
MED0202	El Playon de los Comuneros	MED02
MED0203	Pablo VI	MED02
MED0204	La Frontera	MED02
MED0205	La Francia	MED02
MED0206	Andalucia	MED02
MED0207	Villa del Socorro	MED02
MED0208	Villa Niza	MED02
MED0209	Moscu No.1	MED02
MED0210	Santa Cruz	MED02
MED0211	La Rosa	MED02
MED0301	La Salle	MED03
MED0302	Las Granjas	MED03
MED0303	Campo Valdes No. 2	MED03
MED0304	Santa Ines	MED03
MED0305	Raizal	MED03
MED0306	El Pomar	MED03
MED0307	Manrique Central No.2	MED03
MED0308	Manrique Oriental	MED03
MED0309	Versalles No.1	MED03
MED0310	Versalles No.2	MED03
MED0311	La Cruz	MED03
MED0312	Oriente	MED03
MED0313	Maria Cano Carambolas	MED03
MED0314	San Jose de la Cima No.1	MED03
MED0315	San Jose de la Cima No.2	MED03
MED0401	Berlin	MED04
MED0402	San Isidro	MED04
MED0403	Palermo	MED04
MED0404	Bermejal Los Alamos	MED04
MED0405	Moravia	MED04
MED0407	Sevilla	MED04
MED0408	San Pedro	MED04
MED0409	Manrique Central No.1	MED04
MED0410	Campo Valdes No.1	MED04
MED0411	Las Esmeraldas	MED04
MED0412	La Pinuela	MED04
MED0413	Aranjuez	MED04
MED0414	Brasilia	MED04
MED0415	Miranda	MED04
MED0501	Toscana	MED05
MED0502	Las Brisas	MED05
MED0503	Florencia	MED05
MED0504	Tejelo	MED05
MED0505	Boyaca	MED05
MED0507	Hector Abad Gomez	MED05
MED0508	Belalcazar	MED05
MED0509	Girardot	MED05
MED0510	Tricentenario	MED05
MED0511	Castilla	MED05
MED0513	Francisco Antonio Zea	MED05
MED0514	Alfonso Lopez	MED05
MED0517	Caribe	MED05
MED0519	El Progreso	MED05
MED0601	Santander	MED06
MED0602	Doce de Octubre No.1	MED06
MED0603	Doce de Octubre No.2	MED06
MED0604	Pedregal	MED06
MED0605	La Esperanza	MED06
MED0606	San Martin de Porres	MED06
MED0607	Kennedy	MED06
MED0608	Picacho	MED06
MED0609	Picachito	MED06
MED0610	Mirador del Doce	MED06
MED0611	El Progreso No.2	MED06
MED0612	El Triunfo	MED06
MED0702	Cerro El Volador	MED07
MED0703	San German	MED07
MED0705	Facultad de Minas Universidad Nacional	MED07
MED0706	La Pilarica	MED07
MED0707	Bosques de San Pablo	MED07
MED0708	Altamira	MED07
MED0709	Cordoba	MED07
MED0710	Lopez de Mesa	MED07
MED0711	El Diamante	MED07
MED0712	Aures No.2	MED07
MED0713	Aures No.1	MED07
MED0714	Bello Horizonte	MED07
MED0715	Villa Flora	MED07
MED0716	Palenque	MED07
MED0717	Robledo	MED07
MED0718	Cucaracho	MED07
MED0719	Fuente Clara	MED07
MED0720	Santa Margarita	MED07
MED0722	Olaya Herrera	MED07
MED0723	Pajarito	MED07
MED0724	Monteclaro	MED07
MED0725	Nueva Villa de la Iguana	MED07
MED0801	Villas Hermosa	MED08
MED0802	La Mansion	MED08
MED0803	San Miguel	MED08
MED0804	La Ladera	MED08
MED0805	Batallon Girardot	MED08
MED0806	Llanaditas	MED08
MED0807	Los Mangos	MED08
MED0808	Enciso	MED08
MED0809	Sucre	MED08
MED0810	El Pinal	MED08
MED0811	Trece de Noviembre	MED08
MED0812	La Libertad	MED08
MED0813	Villatina	MED08
MED0814	San Antonio	MED08
MED0815	Las Estancias	MED08
MED0816	Villa Turbay	MED08
MED0817	La Sierra	MED08
MED0819	Villa Liliam	MED08
MED0901	Juan Pablo II	MED09
MED0902	Barrios de Jesus	MED09
MED0903	Bombona No.2	MED09
MED0904	Los Cerros El Vergel	MED09
MED0905	Alejandro Echavarria	MED09
MED0906	Barrio Caycedo	MED09
MED0907	Buenos Aires	MED09
MED0908	Miraflores	MED09
MED0909	Cataluna	MED09
MED0910	La Milagrosa	MED09
MED0911	Gerona	MED09
MED0912	El Salvador	MED09
MED0913	Loreto	MED09
MED0914	Asomadera No.1	MED09
MED0915	Asomadera No.2	MED09
MED0916	Asomadera No.3	MED09
MED0917	Ocho de Marzo	MED09
MED1001	Prado	MED10
MED1003	Jesus Nazareno	MED10
MED1004	El Chagualo	MED10
MED1005	Estacion Villa	MED10
MED1006	San Benito	MED10
MED1007	Guayaquil	MED10
MED1008	Corazon de Jesus	MED10
MED1011	Calle Nueva	MED10
MED1012	Perpetuo Socorro	MED10
MED1013	Barrio Colon	MED10
MED1014	Las Palmas	MED10
MED1015	Bombona No.1	MED10
MED1016	Boston	MED10
MED1017	Los Angeles	MED10
MED1018	Villa Nueva	MED10
MED1019	La Candelaria	MED10
MED1020	San Diego	MED10
MED1101	Carlos E. Restrepo	MED11
MED1102	Suramericana	MED11
MED1103	Naranjal	MED11
MED1104	San Joaquin	MED11
MED1105	Los Conquistadores	MED11
MED1107	Bolivariana	MED11
MED1108	Laureles	MED11
MED1109	Las Acacias	MED11
MED1110	La Castellana	MED11
MED1111	Lorena	MED11
MED1112	El Velodromo	MED11
MED1113	Estadio	MED11
MED1114	Los Colores	MED11
MED1115	Cuarta Brigada	MED11
MED1117	Florida Nueva	MED11
MED1201	Ferrini	MED12
MED1202	Calasanz	MED12
MED1203	Los Pinos	MED12
MED1204	La America	MED12
MED1205	La Floresta	MED12
MED1206	Santa Lucia	MED12
MED1207	El Danubio	MED12
MED1208	Campo Alegre	MED12
MED1209	Santa Monica	MED12
MED1210	Barrio Cristobal	MED12
MED1211	Simon Bolivar	MED12
MED1212	Santa Teresita	MED12
MED1213	Calasanz Parte Alta	MED12
MED1301	El Pesebre	MED13
MED1302	Blanquizal	MED13
MED1303	Santa Rosa de Lima	MED13
MED1304	Los Alcazares	MED13
MED1305	Metropolitano	MED13
MED1306	La Pradera	MED13
MED1307	Juan XXIII La Quiebra	MED13
MED1308	San Javier No.2	MED13
MED1309	San Javier No.1	MED13
MED1310	Veinte de Julio	MED13
MED1311	Belencito	MED13
MED1312	Betania	MED13
MED1313	El Corazon	MED13
MED1314	La Independencia	MED13
MED1315	Nuevos Conquistadores	MED13
MED1316	El Salado	MED13
MED1317	Eduardo Santos	MED13
MED1318	Antonio Narino	MED13
MED1319	El Socorro	MED13
MED1401	Barrio Colombia	MED14
MED1403	Villa Carlota	MED14
MED1404	Castropol	MED14
MED1405	Lalinde	MED14
MED1406	Las Lomas No.1	MED14
MED1407	Las Lomas No.2	MED14
MED1408	Altos del Poblado	MED14
MED1409	El Tesoro	MED14
MED1410	Los Naranjos	MED14
MED1411	Los Balsos No.1	MED14
MED1412	San Lucas	MED14
MED1413	El Diamante No.2	MED14
MED1414	El Castillo	MED14
MED1415	Los Balsos No.2	MED14
MED1416	Alejandria	MED14
MED1417	La Florida	MED14
MED1418	El Poblado	MED14
MED1419	Manila	MED14
MED1420	Astorga	MED14
MED1421	Patio Bonito	MED14
MED1422	La Aguacatala	MED14
MED1423	Santa Maria de los Angeles	MED14
MED1502	Tenche	MED15
MED1503	Trinidad	MED15
MED1504	Santa Fe	MED15
MED1507	Campo Amor	MED15
MED1509	Cristo Rey	MED15
MED1510	Guayabal	MED15
MED1511	La Colina	MED15
MED1601	Fatima	MED16
MED1602	Rosales	MED16
MED1603	Belen	MED16
MED1604	Granada	MED16
MED1605	San Bernardo	MED16
MED1606	Las Playas	MED16
MED1607	Diego Echavarria	MED16
MED1608	La Mota	MED16
MED1609	La Hondonada	MED16
MED1610	El Rincon	MED16
MED1611	La Loma de Los Bernal	MED16
MED1612	La Gloria	MED16
MED1613	Altavista	MED16
MED1614	La Palma	MED16
MED1615	Los Alpes	MED16
MED1616	Las Violetas	MED16
MED1617	Las Mercedes	MED16
MED1618	Nueva Villa del Aburra	MED16
MED1619	Miravalle	MED16
MED1620	El Nogal - Los Almendros	MED16
MED1621	Cerro Nutibara	MED16
MEDC01	Barrios_San Sebastian de Palmitas	MEDC01
MEDC02	Barrios_San Cristobal	MEDC02
MEDC03	Barrios_Altavista	MEDC03
MEDC04	Barrios_San Antonio de Prado	MEDC04
MEDC05	Barrios_Santa Elena	MEDC05
\.


--
-- Data for Name: comunas; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.comunas (id_comuna, nombre, id_municipio) FROM stdin;
MED01	Popular	MED
MED02	Santa Cruz	MED
MED03	Manrique	MED
MED04	Aranjuez	MED
MED05	Castilla	MED
MED06	Doce de Octubre	MED
MED07	Robledo	MED
MED08	Villa Hermosa	MED
MED09	Buenos Aires	MED
MED10	La Candelaria	MED
MED11	Laureles - Estadio	MED
MED12	La AmÃ©rica	MED
MED13	San Javier	MED
MED14	El Poblado	MED
MED15	Guayabal	MED
MED16	BelÃ©n	MED
MEDC01	San SebastiÃ¡n de Palmitas	MED
MEDC02	San CristÃ³bal	MED
MEDC03	Altavista	MED
MEDC04	San Antonio de Prado	MED
MEDC05	Santa Elena	MED
\.


--
-- Data for Name: municipios; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.municipios (id_municipio, nombre) FROM stdin;
MED	MedellÃ­n
BEL	Bello
ITA	ItagÃ¼Ã­
ENV	Envigado
SAB	Sabaneta
EST	La Estrella
CAL	Caldas
COP	Copacabana
GIR	Girardota
BAR	Barbosa
\.


--
-- Data for Name: tipos_motor; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.tipos_motor (id_motorizacion, nombre) FROM stdin;
1	Gasolina
2	Di‚sel
3	El‚ctrico
4	H¡brido
5	H¡brido enchufable
6	Gas natural
7	Hidr¢geno
\.


--
-- Data for Name: tipos_vehiculo; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.tipos_vehiculo (id_tipo_vehiculo, nombre, vulnerabilidad) FROM stdin;
1	Bicicleta	98
2	Bicicleta el‚ctrica	95
3	Motocicleta	90
4	Autom¢vil	40
5	Taxi	40
6	Camioneta	35
7	SUV	38
8	Van	45
9	Cami¢n	50
10	Bus	50
11	Tractocami¢n	55
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.usuarios (id, nombre, username, email, fecha_nacimiento, creado_en, authhash, id_barrio) FROM stdin;
\.


--
-- Data for Name: vehiculos; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.vehiculos (placa, id_usuario, id_tipo_vehiculo, id_motorizacion, marca, modelo, ano) FROM stdin;
\.


--
-- Data for Name: viajes; Type: TABLE DATA; Schema: camiloardila; Owner: -
--

COPY camiloardila.viajes (id_viaje, id_usuario, id_vehiculo, id_ubi_origen, id_ubi_destino, t_estimado, h_inicio, h_fin, id_clima_inicio, id_clima_fin, precipitacion_mm, finalizado, user_rating) FROM stdin;
\.


--
-- Name: tipos_motor_id_motorizacion_seq; Type: SEQUENCE SET; Schema: camiloardila; Owner: -
--

SELECT pg_catalog.setval('camiloardila.tipos_motor_id_motorizacion_seq', 7, true);


--
-- Name: tipos_vehiculo_id_tipo_vehiculo_seq; Type: SEQUENCE SET; Schema: camiloardila; Owner: -
--

SELECT pg_catalog.setval('camiloardila.tipos_vehiculo_id_tipo_vehiculo_seq', 11, true);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: camiloardila; Owner: -
--

SELECT pg_catalog.setval('camiloardila.usuarios_id_seq', 1, false);


--
-- Name: barrios barrios_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.barrios
    ADD CONSTRAINT barrios_pkey PRIMARY KEY (id_barrio);


--
-- Name: comunas comunas_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.comunas
    ADD CONSTRAINT comunas_pkey PRIMARY KEY (id_comuna);


--
-- Name: municipios municipios_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.municipios
    ADD CONSTRAINT municipios_pkey PRIMARY KEY (id_municipio);


--
-- Name: tipos_motor tipos_motor_nombre_key; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.tipos_motor
    ADD CONSTRAINT tipos_motor_nombre_key UNIQUE (nombre);


--
-- Name: tipos_motor tipos_motor_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.tipos_motor
    ADD CONSTRAINT tipos_motor_pkey PRIMARY KEY (id_motorizacion);


--
-- Name: tipos_vehiculo tipos_vehiculo_nombre_key; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.tipos_vehiculo
    ADD CONSTRAINT tipos_vehiculo_nombre_key UNIQUE (nombre);


--
-- Name: tipos_vehiculo tipos_vehiculo_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.tipos_vehiculo
    ADD CONSTRAINT tipos_vehiculo_pkey PRIMARY KEY (id_tipo_vehiculo);


--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.usuarios
    ADD CONSTRAINT usuarios_email_key UNIQUE (email);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_username_key; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.usuarios
    ADD CONSTRAINT usuarios_username_key UNIQUE (username);


--
-- Name: vehiculos vehiculos_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.vehiculos
    ADD CONSTRAINT vehiculos_pkey PRIMARY KEY (placa);


--
-- Name: viajes viajes_pkey; Type: CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.viajes
    ADD CONSTRAINT viajes_pkey PRIMARY KEY (id_viaje);


--
-- Name: usuarios fk_barrio; Type: FK CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.usuarios
    ADD CONSTRAINT fk_barrio FOREIGN KEY (id_barrio) REFERENCES camiloardila.barrios(id_barrio) NOT VALID;


--
-- Name: barrios fk_comuna; Type: FK CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.barrios
    ADD CONSTRAINT fk_comuna FOREIGN KEY (id_comuna) REFERENCES camiloardila.comunas(id_comuna) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: comunas fk_municipio; Type: FK CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.comunas
    ADD CONSTRAINT fk_municipio FOREIGN KEY (id_municipio) REFERENCES camiloardila.municipios(id_municipio) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: vehiculos fk_tipo_motor; Type: FK CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.vehiculos
    ADD CONSTRAINT fk_tipo_motor FOREIGN KEY (id_motorizacion) REFERENCES camiloardila.tipos_motor(id_motorizacion) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: vehiculos fk_tipo_vehiculo; Type: FK CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.vehiculos
    ADD CONSTRAINT fk_tipo_vehiculo FOREIGN KEY (id_tipo_vehiculo) REFERENCES camiloardila.tipos_vehiculo(id_tipo_vehiculo) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: vehiculos fk_usuario; Type: FK CONSTRAINT; Schema: camiloardila; Owner: -
--

ALTER TABLE ONLY camiloardila.vehiculos
    ADD CONSTRAINT fk_usuario FOREIGN KEY (id_usuario) REFERENCES camiloardila.usuarios(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict iFrNTyez58Ft68GRqRfrwmzPofRGXD44H8DpppDiyohdBygqrXaeCCRbr4o8RbK


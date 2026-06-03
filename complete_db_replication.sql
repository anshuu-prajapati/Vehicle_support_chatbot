--
-- PostgreSQL database dump
--

\restrict xzTqk5OdVApGrnTMkQc7vTHYZnLyFbv6tzYqv6UwePGv9foX95tDn39DPndDPAw

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

-- Started on 2026-06-03 11:31:23

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
-- TOC entry 2 (class 3079 OID 16537)
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- TOC entry 5255 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 245 (class 1259 OID 17075)
-- Name: alerts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alerts (
    id integer NOT NULL,
    vehicle_id integer NOT NULL,
    status character varying(50) NOT NULL,
    alert_type character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.alerts OWNER TO postgres;

--
-- TOC entry 244 (class 1259 OID 17074)
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.alerts_id_seq OWNER TO postgres;

--
-- TOC entry 5256 (class 0 OID 0)
-- Dependencies: 244
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- TOC entry 227 (class 1259 OID 16427)
-- Name: chat_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_history (
    id integer NOT NULL,
    user_id integer,
    question text,
    answer text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.chat_history OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16426)
-- Name: chat_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_history_id_seq OWNER TO postgres;

--
-- TOC entry 5257 (class 0 OID 0)
-- Dependencies: 226
-- Name: chat_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_history_id_seq OWNED BY public.chat_history.id;


--
-- TOC entry 233 (class 1259 OID 16502)
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
    id integer NOT NULL,
    phone_number character varying,
    user_message text,
    bot_response text,
    created_at timestamp without time zone
);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 16501)
-- Name: chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_messages_id_seq OWNER TO postgres;

--
-- TOC entry 5258 (class 0 OID 0)
-- Dependencies: 232
-- Name: chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_messages_id_seq OWNED BY public.chat_messages.id;


--
-- TOC entry 235 (class 1259 OID 16514)
-- Name: conversation_states; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation_states (
    legacy_id integer CONSTRAINT conversation_states_id_not_null NOT NULL,
    phone_number character varying(20) NOT NULL,
    current_step character varying(100) NOT NULL,
    context_json json NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    id uuid DEFAULT gen_random_uuid() CONSTRAINT conversation_states_id_not_null1 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.conversation_states OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 16513)
-- Name: conversation_states_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_states_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.conversation_states_id_seq OWNER TO postgres;

--
-- TOC entry 5259 (class 0 OID 0)
-- Dependencies: 234
-- Name: conversation_states_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conversation_states_id_seq OWNED BY public.conversation_states.legacy_id;


--
-- TOC entry 238 (class 1259 OID 16944)
-- Name: driver_workflows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.driver_workflows (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_number character varying(50) NOT NULL,
    driver_name character varying(255),
    driver_phone character varying(50) NOT NULL,
    owner_phone character varying(50) NOT NULL,
    workflow_status character varying(50) DEFAULT 'IN_PROGRESS'::character varying NOT NULL,
    current_step character varying(100) NOT NULL,
    current_location character varying(500),
    issue_description character varying(1000),
    estimated_arrival_time character varying(255),
    troubleshooting_started boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.driver_workflows OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 17093)
-- Name: fleet_conversations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fleet_conversations (
    id integer NOT NULL,
    phone character varying(20) NOT NULL,
    vehicle_id integer,
    state character varying(100) NOT NULL,
    metadata json NOT NULL
);


ALTER TABLE public.fleet_conversations OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 17092)
-- Name: fleet_conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.fleet_conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fleet_conversations_id_seq OWNER TO postgres;

--
-- TOC entry 5260 (class 0 OID 0)
-- Dependencies: 246
-- Name: fleet_conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.fleet_conversations_id_seq OWNED BY public.fleet_conversations.id;


--
-- TOC entry 223 (class 1259 OID 16402)
-- Name: machines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.machines (
    id integer NOT NULL,
    model_name character varying(100),
    serial_number character varying(100),
    owner_id integer
);


ALTER TABLE public.machines OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16401)
-- Name: machines_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.machines_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.machines_id_seq OWNER TO postgres;

--
-- TOC entry 5261 (class 0 OID 0)
-- Dependencies: 222
-- Name: machines_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.machines_id_seq OWNED BY public.machines.id;


--
-- TOC entry 237 (class 1259 OID 16916)
-- Name: owner_workflows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.owner_workflows (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_number character varying(50) NOT NULL,
    owner_phone character varying(50) NOT NULL,
    workflow_status character varying(50) DEFAULT 'IN_PROGRESS'::character varying NOT NULL,
    current_step character varying(100) NOT NULL,
    current_location character varying(500),
    issue_description character varying(1000),
    assigned_contact_name character varying(255),
    assigned_contact_phone character varying(50),
    driver_name character varying(255),
    driver_phone character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.owner_workflows OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16417)
-- Name: problems; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.problems (
    id integer NOT NULL,
    title character varying(255),
    description text,
    severity character varying(50),
    machine_model character varying(100)
);


ALTER TABLE public.problems OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16416)
-- Name: problems_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.problems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.problems_id_seq OWNER TO postgres;

--
-- TOC entry 5262 (class 0 OID 0)
-- Dependencies: 224
-- Name: problems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.problems_id_seq OWNED BY public.problems.id;


--
-- TOC entry 231 (class 1259 OID 16456)
-- Name: solutions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.solutions (
    id integer NOT NULL,
    problem_id integer,
    step_number integer,
    description text
);


ALTER TABLE public.solutions OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 16455)
-- Name: solutions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.solutions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.solutions_id_seq OWNER TO postgres;

--
-- TOC entry 5263 (class 0 OID 0)
-- Dependencies: 230
-- Name: solutions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.solutions_id_seq OWNED BY public.solutions.id;


--
-- TOC entry 229 (class 1259 OID 16443)
-- Name: tickets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tickets (
    id integer NOT NULL,
    user_id integer,
    issue character varying(255),
    status character varying(50)
);


ALTER TABLE public.tickets OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 16442)
-- Name: tickets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tickets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tickets_id_seq OWNER TO postgres;

--
-- TOC entry 5264 (class 0 OID 0)
-- Dependencies: 228
-- Name: tickets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tickets_id_seq OWNED BY public.tickets.id;


--
-- TOC entry 221 (class 1259 OID 16390)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying,
    phone character varying,
    role character varying(20) DEFAULT 'driver'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16389)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 5265 (class 0 OID 0)
-- Dependencies: 220
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 239 (class 1259 OID 16969)
-- Name: vehicle_contacts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_contacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_number character varying(50) NOT NULL,
    owner_phone character varying(50) NOT NULL,
    driver_phone character varying(50),
    contact_type character varying(50) NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vehicle_contacts OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 16888)
-- Name: vehicle_monitoring; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_monitoring (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_number character varying(50) NOT NULL,
    vehicle_imei character varying(100),
    status character varying(50) NOT NULL,
    last_seen_at timestamp with time zone,
    last_location jsonb,
    owner_name character varying(255),
    owner_phone character varying(50),
    driver_name character varying(255),
    driver_phone character varying(50),
    issue_detected_at timestamp with time zone DEFAULT now() NOT NULL,
    notification_sent boolean DEFAULT false NOT NULL,
    ticket_created boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vehicle_monitoring OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 17056)
-- Name: vehicle_statuses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_statuses (
    id integer NOT NULL,
    vehicle_id integer NOT NULL,
    ign_state character varying(20),
    mode character varying(50),
    location character varying(255),
    last_gps_time timestamp with time zone,
    not_working_hours integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.vehicle_statuses OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 17055)
-- Name: vehicle_statuses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicle_statuses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_statuses_id_seq OWNER TO postgres;

--
-- TOC entry 5266 (class 0 OID 0)
-- Dependencies: 242
-- Name: vehicle_statuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicle_statuses_id_seq OWNED BY public.vehicle_statuses.id;


--
-- TOC entry 241 (class 1259 OID 17029)
-- Name: vehicles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicles (
    id integer NOT NULL,
    vehicle_number character varying(100) NOT NULL,
    manager_id integer,
    supervisor_id integer,
    driver_id integer
);


ALTER TABLE public.vehicles OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 17028)
-- Name: vehicles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicles_id_seq OWNER TO postgres;

--
-- TOC entry 5267 (class 0 OID 0)
-- Dependencies: 240
-- Name: vehicles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicles_id_seq OWNED BY public.vehicles.id;


--
-- TOC entry 5001 (class 2604 OID 17078)
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- TOC entry 4970 (class 2604 OID 16430)
-- Name: chat_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history ALTER COLUMN id SET DEFAULT nextval('public.chat_history_id_seq'::regclass);


--
-- TOC entry 4974 (class 2604 OID 16505)
-- Name: chat_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ALTER COLUMN id SET DEFAULT nextval('public.chat_messages_id_seq'::regclass);


--
-- TOC entry 4975 (class 2604 OID 16517)
-- Name: conversation_states legacy_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_states ALTER COLUMN legacy_id SET DEFAULT nextval('public.conversation_states_id_seq'::regclass);


--
-- TOC entry 5003 (class 2604 OID 17096)
-- Name: fleet_conversations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fleet_conversations ALTER COLUMN id SET DEFAULT nextval('public.fleet_conversations_id_seq'::regclass);


--
-- TOC entry 4968 (class 2604 OID 16405)
-- Name: machines id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machines ALTER COLUMN id SET DEFAULT nextval('public.machines_id_seq'::regclass);


--
-- TOC entry 4969 (class 2604 OID 16420)
-- Name: problems id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.problems ALTER COLUMN id SET DEFAULT nextval('public.problems_id_seq'::regclass);


--
-- TOC entry 4973 (class 2604 OID 16459)
-- Name: solutions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.solutions ALTER COLUMN id SET DEFAULT nextval('public.solutions_id_seq'::regclass);


--
-- TOC entry 4972 (class 2604 OID 16446)
-- Name: tickets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tickets ALTER COLUMN id SET DEFAULT nextval('public.tickets_id_seq'::regclass);


--
-- TOC entry 4965 (class 2604 OID 16393)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 4999 (class 2604 OID 17059)
-- Name: vehicle_statuses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_statuses ALTER COLUMN id SET DEFAULT nextval('public.vehicle_statuses_id_seq'::regclass);


--
-- TOC entry 4998 (class 2604 OID 17032)
-- Name: vehicles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles ALTER COLUMN id SET DEFAULT nextval('public.vehicles_id_seq'::regclass);


--
-- TOC entry 5247 (class 0 OID 17075)
-- Dependencies: 245
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.alerts VALUES (1, 1, 'OPEN', 'VEHICLE_OFF_NOT_WORKING', '2026-06-03 06:12:37.481801+05:30');


--
-- TOC entry 5229 (class 0 OID 16427)
-- Dependencies: 227
-- Data for Name: chat_history; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5235 (class 0 OID 16502)
-- Dependencies: 233
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.chat_messages VALUES (1, '918882374849', 'Machine becomes very hot', '
        Problem: Machine Overheating
        
        Description:
        Machine gets hot after 1 hour of operation
        
        Solutions:
        
        1. Clean cooling vents
2. Check coolant circulation
3. Inspect cooling fan
', '2026-05-29 10:09:21.83638');
INSERT INTO public.chat_messages VALUES (2, '918882374849', 'hii', 'Hello, I''m here to help with your machine issue. You''re experiencing overheating after 1 hour of operation. Can you tell me a bit more about what you''ve observed and if you''ve tried anything to resolve it so far?', '2026-05-29 11:08:18.891453');
INSERT INTO public.chat_messages VALUES (3, '918882374849', 'Machine becomes very hot', '"Hi, thanks for reporting the issue. Machine overheating can be caused by blocked cooling vents, poor coolant circulation, or a faulty cooling fan. Can you try cleaning the cooling vents and check if the cooling fan is working properly? If the issue persists, we can schedule a maintenance check to inspect the coolant circulation system."', '2026-05-29 11:09:25.712428');
INSERT INTO public.chat_messages VALUES (4, '918882374849', 'Heyy', 'Hi, I''m here to help with your machine issue. You mentioned it''s overheating after 1 hour of operation. Can you tell me more about the problem, like any error messages or unusual noises?', '2026-05-29 11:29:25.986817');
INSERT INTO public.chat_messages VALUES (5, '918882374849', 'meri machine gram ho gyi hai', 'Namaste, aapki machine ko overheating ka issue ho raha hai. Humne aise cases dekhe hain. Kya aapne cooling vents ko clean kiya hai? Ya phir coolant circulation aur cooling fan ko inspect kiya hai? Hum aapki madad kar sakte hain.', '2026-05-29 11:36:47.390693');
INSERT INTO public.chat_messages VALUES (6, '918882374849', 'cooling vents ye kha hota hai', 'Cooling vents machine ke andar hoti hain jo garmi ko bahar nikaalti hain. Agar ye vents gande ho jayein, to machine overheating ka problem aa sakta hai. Main suggest karta hoon ki aap cooling vents ko saaf karein aur dekhein ki problem solve hoti hai ya nahi.', '2026-05-29 11:37:14.615454');
INSERT INTO public.chat_messages VALUES (7, '918882374849', 'hi', 'Hi, thanks for reaching out. I''d be happy to help with your machine overheating issue. Can you tell me more about the problem? You mentioned it gets hot after 1 hour of operation, is that correct?', '2026-05-29 11:38:58.992035');
INSERT INTO public.chat_messages VALUES (8, '918882374849', 'yes it is heated because of weather i guess', 'That''s a good point about the weather. However, to rule out any machine-related issues, I''d still recommend checking the cooling vents, coolant circulation, and cooling fan to ensure they''re functioning properly. Can you try cleaning the vents and inspecting the fan to see if that makes a difference?', '2026-05-29 11:42:01.441829');
INSERT INTO public.chat_messages VALUES (9, '918882374849', 'yes my coolant isnot working', 'The coolant not working is likely the root cause of the overheating issue. I recommend checking the coolant reservoir level, hoses, and pump for any blockages or leaks. Also, ensure the coolant pump is functioning correctly. If you''re not comfortable with this, I can schedule a site visit to assist with the repair. Would you like me to arrange that?', '2026-05-29 11:42:24.984382');
INSERT INTO public.chat_messages VALUES (10, '+918882374849', 'heyy', 'Namaste sir/ma''am ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-05-30 16:45:19.019402');
INSERT INTO public.chat_messages VALUES (11, '+918882374849', 'problem hai jcb me', 'Sirf 1 ya 2 bhejein.
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-05-30 16:45:35.664612');
INSERT INTO public.chat_messages VALUES (12, '+918882374849', '1', 'Thik hai. Kripya machine ka problem ek line mein batayein.', '2026-05-30 16:45:45.802892');
INSERT INTO public.chat_messages VALUES (13, '+918882374849', 'machine gram ho rahi hai', 'Machine overheating issue. Kya aapne cooling vents saaf kiye hain? Ya phir coolant circulation aur cooling fan ki inspection karwaai hai?', '2026-05-30 16:46:06.797046');
INSERT INTO public.chat_messages VALUES (14, '+918882374849', 'haa colling vent saanf kar liye but kuch farak nahi pda', 'Vents saaf karne ke baad bhi overheating issue resolve nahi hua? Ab next step hai coolant circulation check karna. Kya aap coolant level aur circulation system check kar sakte hain? Ya phir cooling fan ka inspection karne ki zarurat hai.', '2026-05-30 16:46:40.648587');
INSERT INTO public.chat_messages VALUES (15, '+918882374849', 'kaise check karu', '"Machine overheating ka issue hai. Cooling system check karna hoga. Pehle cooling vents ko saaf karein, phir coolant circulation ko inspect karein, aur last mein cooling fan ki condition check karein. Agar problem solve na ho to mujhe details share karein, main further assistance provide karunga."', '2026-05-30 16:47:04.032516');
INSERT INTO public.chat_messages VALUES (16, '+918882374849', 'sab klar liya kuch nahi ho raha', 'Machine overheating issue ko solve karne ke liye maine 3 steps suggest kiye the. Kya aapne unhe try kiya? 
1. Cooling vents ko clean kiya?
2. Coolant circulation ko check kiya?
3. Cooling fan ko inspect kiya? 
Please confirm, taaki hum agle steps discuss kar sakein.', '2026-05-30 16:47:31.953776');
INSERT INTO public.chat_messages VALUES (17, '+918882374849', 'haa tino kar liye', 'Machine overheating issue. I''ve noted the problem. To resolve, I recommend: 
1. Cleaning cooling vents 
2. Checking coolant circulation 
3. Inspecting cooling fan 
Let me know if you''ve tried any of these steps already.', '2026-05-30 16:47:56.104727');
INSERT INTO public.chat_messages VALUES (18, '+918882374849', '1,2,3', 'To address the machine overheating issue, I recommend the following steps: 
1. Clean the cooling vents to ensure proper airflow.
2. Check the coolant circulation system for any blockages or leaks.
3. Inspect the cooling fan for damage or malfunction. Let me know if you need assistance with these steps.', '2026-05-30 16:48:11.04916');
INSERT INTO public.chat_messages VALUES (19, '+918882374849', 'nahi ho raha sab klkar liya mujhe btao aage kya karu mai', 'Machine overheating ke liye maine 3 solutions di hai: 
1. Cooling vents ko saaf karo
2. Coolant circulation ko check karo
3. Cooling fan ko inspect karo

Aap inme se ek-ek karke try karo aur dekho ki machine ka temperature control ho raha hai ya nahi. Agar phir bhi problem rahe toh mujhe update karo, main aage ki guidance dunga.', '2026-05-30 16:48:39.831717');
INSERT INTO public.chat_messages VALUES (20, '+918882374849', 'ye 3 kar liye kuch nahi hua', 'Agar ye 3 steps karne ke baad bhi machine overheating ka issue resolve nahi hua, to humein machine ki detailed inspection karni padegi. Main kuch aur questions puchhna chahta hoon: 
1. Machine ka model number kya hai? 
2. Kab se ye issue aa raha hai? 
3. Kya machine ka maintenance schedule follow kiya ja raha hai? 

Please apne sawal ka jawab den, taaki hum is issue ko solve kar sakein.', '2026-05-30 16:49:05.200271');
INSERT INTO public.chat_messages VALUES (21, '+918882374849', '1 JCB321
2. 15 days se
3. haa but driver thoda lazy hai', 'Hello, thanks for reaching out. Sorry to hear that your JCB321 is overheating after 1 hour of operation. Can you please try cleaning the cooling vents, checking the coolant circulation, and inspecting the cooling fan? Also, please ensure the driver is operating the machine as per the guidelines. If the issue persists, we can schedule a maintenance check.', '2026-05-30 16:49:50.233658');
INSERT INTO public.chat_messages VALUES (22, '+918882374849', 'heyy', 'Namaste +918882374849 ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-05-31 05:05:20.558528');
INSERT INTO public.chat_messages VALUES (23, '+918882374849', 'who ??', 'Sirf 1 ya 2 bhejein.
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-05-31 05:07:22.549483');
INSERT INTO public.chat_messages VALUES (24, '+918882374849', '2', 'Kya driver machine ke paas hai? Haan / Nahi', '2026-05-31 07:58:57.725563');
INSERT INTO public.chat_messages VALUES (25, '+918882374849', 'nahi', 'Theek hai. Driver ready ho tab aap dobara message bhej sakte hain.', '2026-05-31 07:59:09.255181');
INSERT INTO public.chat_messages VALUES (26, '+918882374849', 'mai khud hi karungi', 'Sirf 1 ya 2 bhejein.
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-05-31 07:59:25.879416');
INSERT INTO public.chat_messages VALUES (27, '+918882374849', '1', 'Thik hai. Kripya machine ka problem ek line mein batayein.', '2026-05-31 07:59:34.075721');
INSERT INTO public.chat_messages VALUES (28, '+918882374849', 'hii', 'Hi, thanks for reaching out. Your machine is overheating after 1 hour of operation, right? I''d recommend checking the cooling vents for blockages, verifying coolant circulation, and inspecting the cooling fan for any issues. Can you try these steps and let me know the results?

Kya problem solve hui? Haan / Nahi', '2026-06-01 05:28:48.955495');
INSERT INTO public.chat_messages VALUES (29, '+918882374849', 'hi', 'Kripya sirf Haan ya Nahi mein reply dein. Kya problem solve hui?', '2026-06-01 05:44:37.903968');
INSERT INTO public.chat_messages VALUES (30, '+918882374849', 'hii', 'Namaste +918882374849 ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-01 05:48:57.696767');
INSERT INTO public.chat_messages VALUES (31, '+918882374849', 'hi', 'Namaste +918882374849 ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-01 05:49:22.799076');
INSERT INTO public.chat_messages VALUES (32, '+918882374849', '1.', 'Thik hai. Kripya machine ka problem ek line mein batayein.', '2026-06-01 05:49:50.431162');
INSERT INTO public.chat_messages VALUES (33, '+918882374849', 'hii', 'Namaste +918882374849 ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-01 08:21:06.996477');
INSERT INTO public.chat_messages VALUES (34, '+918882374849', 'hii', 'Namaste +918882374849 ji 👋
Aapko kis tarah ki madad chahiye?
1. Machine issue
2. Engineer chahiye', '2026-06-01 08:58:19.391865');
INSERT INTO public.chat_messages VALUES (35, '+918882374849', '1', 'Kripya apni machine ka vehicle number bhejiye.', '2026-06-01 08:58:49.854019');
INSERT INTO public.chat_messages VALUES (36, '+918882374849', 'UP32AB1234', 'Dhanyavaad. Kya driver machine ke paas hai? Haan / Nahi', '2026-06-01 09:00:39.74296');
INSERT INTO public.chat_messages VALUES (37, '+918882374849', 'haa', 'Bataiye, machine ka location kya hai?', '2026-06-01 09:00:49.063551');
INSERT INTO public.chat_messages VALUES (38, '+918882374849', 'Lodhi garden', 'Kya ignition on hai? Haan / Nahi', '2026-06-01 09:02:20.235114');
INSERT INTO public.chat_messages VALUES (39, '+918882374849', 'Haa', 'Kya power LED jal rahi hai? Haan / Nahi', '2026-06-01 09:07:59.937062');
INSERT INTO public.chat_messages VALUES (40, '+918882374849', 'Haa', 'Kya GSM LED jal rahi hai? Haan / Nahi', '2026-06-01 09:08:06.821565');
INSERT INTO public.chat_messages VALUES (41, '+918882374849', 'Nahi', 'Kya GPS LED jal rahi hai? Haan / Nahi', '2026-06-01 09:08:14.020426');
INSERT INTO public.chat_messages VALUES (42, '+918882374849', 'Nhi', 'Kya problem solve ho gayi? Haan / Nahi', '2026-06-01 09:08:21.15848');
INSERT INTO public.chat_messages VALUES (43, '+918882374849', 'hii', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-01 09:12:24.964077');
INSERT INTO public.chat_messages VALUES (44, '+918882374849', '1', 'Kripya vehicle number bataye.
Example:
DL01AB1234', '2026-06-01 09:13:26.220612');
INSERT INTO public.chat_messages VALUES (45, '+918882374849', 'UP32AB1234', 'Kripya driver vehicle ke paas hai?
1️⃣ Haan
2️⃣ Nahi', '2026-06-01 09:14:04.169115');
INSERT INTO public.chat_messages VALUES (46, '+918882374849', 'hii', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-01 09:16:16.781617');
INSERT INTO public.chat_messages VALUES (47, '+918882374849', '5', 'Kripya valid option select kare.

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye', '2026-06-01 09:16:22.971928');
INSERT INTO public.chat_messages VALUES (48, '+918882374849', 'hii', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-01 15:42:47.690549');
INSERT INTO public.chat_messages VALUES (49, '+918882374849', '1', 'Kripya vehicle number bataye.
Example:
DL01AB1234', '2026-06-01 15:43:47.634463');
INSERT INTO public.chat_messages VALUES (50, '+918882374849', 'egghjkj3257bbj', 'Kripya driver vehicle ke paas hai?
1️⃣ Haan
2️⃣ Nahi', '2026-06-01 15:43:58.326728');
INSERT INTO public.chat_messages VALUES (51, '+918882374849', 'haan', 'Bataiye vehicle ka location kya hai?', '2026-06-01 15:44:10.043245');
INSERT INTO public.chat_messages VALUES (52, '+918882374849', 'delhi me hai abhi', 'Kya ignition on hai? Haan / Nahi', '2026-06-01 15:44:30.385256');
INSERT INTO public.chat_messages VALUES (53, '+918882374849', 'nahi', 'Kya power LED jal rahi hai? Haan / Nahi', '2026-06-01 15:44:41.86672');
INSERT INTO public.chat_messages VALUES (54, '+918882374849', 'hii', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-02 08:27:43.795');
INSERT INTO public.chat_messages VALUES (55, '+918882374849', '1', 'Kripya vehicle number bataye.
Example:
DL01AB1234', '2026-06-02 08:28:07.823264');
INSERT INTO public.chat_messages VALUES (56, '+918882374849', 'hii', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-02 09:36:46.594876');
INSERT INTO public.chat_messages VALUES (57, '+918882374849', '1', 'Kripya vehicle number bataye.
Example:
DL01AB1234', '2026-06-02 09:36:54.865705');
INSERT INTO public.chat_messages VALUES (58, '+918882374849', 'Hello', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-02 10:04:15.174495');
INSERT INTO public.chat_messages VALUES (59, '+918882374849', 'HII', 'Namaste +918882374849 Ji 👋

Aapko kis tarah ki madad chahiye?

1️⃣ Vehicle Problem

2️⃣ Engineer Chahiye

Reply with 1 or 2.', '2026-06-02 10:13:45.838722');
INSERT INTO public.chat_messages VALUES (60, '+918882374849', '1', 'Kripya vehicle number bataye.
Example:
DL01AB1234', '2026-06-02 10:13:51.165373');
INSERT INTO public.chat_messages VALUES (61, '+918882374849', 'UP32AB1234', 'Kripya driver vehicle ke paas hai?
1️⃣ Haan
2️⃣ Nahi', '2026-06-02 10:13:56.619742');
INSERT INTO public.chat_messages VALUES (62, '+918882374849', 'nahi', 'Kripya owner ka naam aur phone number bhejiye.', '2026-06-02 10:14:08.738527');
INSERT INTO public.chat_messages VALUES (63, '+918882374849', 'Sarvesh,
918290323758', 'Koi active owner workflow nahi mila.
Kripya phir se check karein ya support team se sampark karein.', '2026-06-02 10:14:35.506176');
INSERT INTO public.chat_messages VALUES (64, '+918882374849', 'haan driver vehicle ke pass hai', 'Koi active owner workflow nahi mila.
Kripya phir se check karein ya support team se sampark karein.', '2026-06-02 10:16:40.458228');
INSERT INTO public.chat_messages VALUES (65, '+918882374849', '1', 'Theek hai.

Vehicle ki current location share kare.
Address ya latitude-longitude bhej sakte hain.', '2026-06-02 10:37:00.611544');
INSERT INTO public.chat_messages VALUES (66, '+918882374849', 'Karol bagh', 'Main kisse baat karun?

1️⃣ Main khud jankari dunga
2️⃣ Driver se baat kare', '2026-06-02 10:37:46.933474');
INSERT INTO public.chat_messages VALUES (67, '+918882374849', '1', 'Problem kya aa rahi hai?', '2026-06-02 10:38:01.652187');
INSERT INTO public.chat_messages VALUES (68, '+918882374849', 'Machine chalu nahi ho rahi', 'Namaste, UP32AB1234 owner support. Sorry to hear your machine isn''t starting. Can you please provide more details about the issue? Is it giving any error messages or making unusual noises? Also, has the machine been serviced recently? I''ll do my best to assist you.

Kya problem solve hui?

1️⃣ Haan
2️⃣ Nahi', '2026-06-02 10:38:16.983314');
INSERT INTO public.chat_messages VALUES (69, '+918882374849', 'Nahi', 'Kripya sirf 1, 2 ya 3 ka reply dein.
1️⃣ Haan, main coordinate karunga
2️⃣ Kisi aur vyakti se baat kare
3️⃣ Driver se seedha baat kare', '2026-06-02 10:38:38.218656');
INSERT INTO public.chat_messages VALUES (70, '+918882374849', '1', 'Koi active owner workflow nahi mila.
Kripya phir se check karein ya support team se sampark karein.', '2026-06-02 11:25:11.85431');
INSERT INTO public.chat_messages VALUES (71, '+918882374849', 'hii', 'Namaste +918882374849 ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-02 12:34:02.05081');
INSERT INTO public.chat_messages VALUES (72, '+918882374849', 'investigate', 'Sirf 1 ya 2 bhejein.
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-02 17:44:26.875192');
INSERT INTO public.chat_messages VALUES (73, '+918882374849', '2', 'Kya driver machine ke paas hai? Haan / Nahi', '2026-06-02 17:45:00.553973');
INSERT INTO public.chat_messages VALUES (74, '+918882374849', 'haan', 'Kripya valid reason bhejein. Options: Breakdown, Maintenance, Waiting Load, Leave, Other.', '2026-06-02 17:45:13.353363');
INSERT INTO public.chat_messages VALUES (75, '+918882374849', 'keave', 'Kripya valid reason bhejein. Options: Breakdown, Maintenance, Waiting Load, Leave, Other.', '2026-06-02 17:45:29.02072');
INSERT INTO public.chat_messages VALUES (76, '+918882374849', 'Leave', 'Aapka current location kya hai?', '2026-06-02 17:45:44.597827');
INSERT INTO public.chat_messages VALUES (77, '+918882374849', 'karol bagh', 'Kripya sirf Haan ya Nahi bhejein. Kya driver machine ke paas hai?', '2026-06-02 17:47:02.561736');
INSERT INTO public.chat_messages VALUES (78, '+919999999999', '3', 'Driver ko alert bhej diya gaya hai. Ab driver se investigation karwayein.', '2026-06-03 00:45:03.823839');
INSERT INTO public.chat_messages VALUES (79, '+918888888888', 'Breakdown', 'Namaste Test Driver ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-03 00:45:39.795025');
INSERT INTO public.chat_messages VALUES (80, '+918882374849', '3', 'Kripya sirf Haan ya Nahi bhejein. Kya driver machine ke paas hai?', '2026-06-03 00:47:13.860965');
INSERT INTO public.chat_messages VALUES (81, '+918882374849', 'nahi', 'Theek hai. Driver ready ho tab aap dobara message bhej sakte hain.', '2026-06-03 00:47:28.998267');
INSERT INTO public.chat_messages VALUES (82, '+918882374849', 'hii', 'Namaste Test Manager ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-03 00:47:42.528024');
INSERT INTO public.chat_messages VALUES (83, '+918882374849', '1', 'Thik hai. Kripya machine ka problem ek line mein batayein.', '2026-06-03 00:47:55.10699');
INSERT INTO public.chat_messages VALUES (84, '+919999999999', '3', 'Driver ko contact kar diya gaya hai.
Aapka update note kar liya gaya hai.
Agar issue close ho gaya ho toh ''closed'' bhejiye.', '2026-06-03 00:48:06.702684');
INSERT INTO public.chat_messages VALUES (85, '+918888888888', 'Breakdown', 'Sirf 1 ya 2 bhejein.
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-03 00:49:44.043131');
INSERT INTO public.chat_messages VALUES (86, '+918888888888', 'Breakdown', 'Sirf 1 ya 2 bhejein.
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-03 00:50:05.960791');
INSERT INTO public.chat_messages VALUES (87, '+918882374849', '3', '"Hi, for the machine overheating issue, I recommend inspecting the cooling fan to ensure it''s working properly and not blocked by debris. This should help prevent overheating after 1 hour of operation. Would you like me to guide you through the inspection process?"

Kya problem solve hui? Haan / Nahi', '2026-06-03 01:15:42.557273');
INSERT INTO public.chat_messages VALUES (88, '+918882374849', '3', 'Kripya sirf Haan ya Nahi mein reply dein. Kya problem solve hui?', '2026-06-03 01:15:44.221054');
INSERT INTO public.chat_messages VALUES (89, '+1234567890', 'test', 'Namaste +1234567890 ji 👋
Aapko kis tarah ki madad chahiye?
1. Problem batani hai
2. Engineer chahiye', '2026-06-03 01:17:00.728787');


--
-- TOC entry 5237 (class 0 OID 16514)
-- Dependencies: 235
-- Data for Name: conversation_states; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.conversation_states VALUES (11, '+919999999999', 'CONTACT_DRIVER', '{"alert_id": 1, "vehicle_id": 1, "vehicle_number": "TEST-100", "driver_name": "Test Driver", "current_location": "Test Depot", "last_gps_time": "2026-06-03 00:42:37", "driver_phone": "+918888888888", "manager_phone": "+919999999999"}', '2026-06-03 06:15:01.61231+05:30', '3c856b46-6613-41c7-831c-063b22ec4296', '2026-06-03 06:12:37.579324+05:30');
INSERT INTO public.conversation_states VALUES (12, '+918888888888', 'ask_help_type', '{"user_name": "Test Driver"}', '2026-06-03 06:15:38.623901+05:30', '513d2601-edfc-4fae-a77d-ca69d8bd33ac', '2026-06-03 06:15:38.623901+05:30');
INSERT INTO public.conversation_states VALUES (8, '+918290323758', 'DRIVER_START', '{"location": "", "ticket_id": "", "issue_type": "", "owner_name": "", "driver_name": "Rahul", "owner_phone": "+918882374849", "driver_phone": "+918290323758", "last_location": "", "last_seen_time": "", "vehicle_number": "UP32AB1234", "current_location": "", "last_ai_response": "", "issue_description": "", "assigned_contact_name": "", "assigned_contact_phone": "", "estimated_arrival_time": "", "troubleshooting_history": ""}', '2026-06-02 16:06:40.044749+05:30', '6df27b51-deba-4e03-b93f-7d6edae1fee3', '2026-06-02 16:06:40.044749+05:30');
INSERT INTO public.conversation_states VALUES (13, '+918882374849', 'confirm_troubleshoot', '{"user_name": "Test Manager", "problem_text": "3"}', '2026-06-03 06:45:40.471062+05:30', '8ba80b5b-b653-4023-96f6-29281e7a300a', '2026-06-03 06:17:40.208645+05:30');
INSERT INTO public.conversation_states VALUES (14, '+1234567890', 'ask_help_type', '{"user_name": "+1234567890"}', '2026-06-03 06:46:59.486443+05:30', 'dd3e89d0-1ddd-4383-8a15-24485805b1ea', '2026-06-03 06:46:59.486443+05:30');
INSERT INTO public.conversation_states VALUES (10, '+918882374849', 'ask_driver_location', '{"driver_investigation": {"stop_reason": "leave"}}', '2026-06-02 23:15:42.995088+05:30', '6370e8bc-dc8d-47d4-978c-ed97e81d123d', '2026-06-02 22:56:19.044051+05:30');


--
-- TOC entry 5240 (class 0 OID 16944)
-- Dependencies: 238
-- Data for Name: driver_workflows; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.driver_workflows VALUES ('d2c1653c-f768-44d3-a10c-d3f7923e2987', 'UP32AB1234', 'Rahul', '+918290323758', '+918882374849', 'IN_PROGRESS', 'DRIVER_START', NULL, NULL, NULL, false, '2026-06-02 16:06:38.405473+05:30', '2026-06-02 16:06:38.405473+05:30');


--
-- TOC entry 5249 (class 0 OID 17093)
-- Dependencies: 247
-- Data for Name: fleet_conversations; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5225 (class 0 OID 16402)
-- Dependencies: 223
-- Data for Name: machines; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5239 (class 0 OID 16916)
-- Dependencies: 237
-- Data for Name: owner_workflows; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.owner_workflows VALUES ('d50d4abb-ecd7-4aba-929e-da992c03b947', 'UP32AB1234', '+918882374849', 'IN_PROGRESS', 'OWNER_SELF_SUPPORT_CONFIRMATION', 'Karol bagh', 'Machine chalu nahi ho rahi', NULL, NULL, 'Rahul', '+918290323758', '2026-06-02 16:06:38.395104+05:30', '2026-06-02 10:38:14.334161+05:30');
INSERT INTO public.owner_workflows VALUES ('6db58242-e1d0-41b5-ac67-b208ffc0599a', 'UP32AB1234', '+918882374849', 'IN_PROGRESS', 'OWNER_CONFIRMATION', NULL, NULL, NULL, NULL, 'Rahul', '+918290323758', '2026-06-02 16:54:53.923287+05:30', '2026-06-02 16:54:53.923287+05:30');
INSERT INTO public.owner_workflows VALUES ('ae999669-9a7b-4d32-bf30-1f4abae8ed1e', 'UP32AB1234', '+918882374849', 'IN_PROGRESS', 'OWNER_CONFIRMATION', NULL, NULL, NULL, NULL, 'Rahul', '+918290323758', '2026-06-02 17:13:39.408386+05:30', '2026-06-02 17:13:39.408386+05:30');


--
-- TOC entry 5227 (class 0 OID 16417)
-- Dependencies: 225
-- Data for Name: problems; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.problems VALUES (1, 'Machine Overheating', 'Machine gets hot after 1 hour of operation', 'Medium', 'CNC-X1');


--
-- TOC entry 5233 (class 0 OID 16456)
-- Dependencies: 231
-- Data for Name: solutions; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.solutions VALUES (1, 1, 1, 'Clean cooling vents');
INSERT INTO public.solutions VALUES (2, 1, 2, 'Check coolant circulation');
INSERT INTO public.solutions VALUES (3, 1, 3, 'Inspect cooling fan');


--
-- TOC entry 5231 (class 0 OID 16443)
-- Dependencies: 229
-- Data for Name: tickets; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5223 (class 0 OID 16390)
-- Dependencies: 221
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.users VALUES (4, 'Test Driver', '+9999999999', 'driver', '2026-06-01 13:52:47.537491');
INSERT INTO public.users VALUES (5, 'Test Manager', '+919999999999', 'manager', '2026-06-03 06:12:37.452706');
INSERT INTO public.users VALUES (6, 'Test Driver', '+918888888888', 'customer', '2026-06-03 06:12:37.458713');
INSERT INTO public.users VALUES (3, 'Test Manager', '+918882374849', 'manager', '2026-06-01 13:51:05.036741');
INSERT INTO public.users VALUES (7, 'Test Driver', '+918290323758', 'customer', '2026-06-03 06:14:39.626184');
INSERT INTO public.users VALUES (8, '+1234567890', '+1234567890', 'customer', '2026-06-03 06:46:59.47936');


--
-- TOC entry 5241 (class 0 OID 16969)
-- Dependencies: 239
-- Data for Name: vehicle_contacts; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.vehicle_contacts VALUES ('b02b3bce-04ed-4dff-922b-f1fb840ba138', 'UP32AB1234', '+918882374849', '+918290323758', 'OWNER', true, '2026-06-02 16:06:40.025178+05:30', '2026-06-02 16:06:40.025178+05:30');
INSERT INTO public.vehicle_contacts VALUES ('12ec2020-f55b-47a1-adaf-f36696c0955b', 'UP32AB1234', '+918882374849', '+918290323758', 'DRIVER', true, '2026-06-02 16:06:40.037148+05:30', '2026-06-02 16:06:40.037148+05:30');


--
-- TOC entry 5238 (class 0 OID 16888)
-- Dependencies: 236
-- Data for Name: vehicle_monitoring; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5245 (class 0 OID 17056)
-- Dependencies: 243
-- Data for Name: vehicle_statuses; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.vehicle_statuses VALUES (1, 1, 'off', 'not working', 'Test Depot', '2026-06-03 01:02:43.2148+05:30', 0);


--
-- TOC entry 5243 (class 0 OID 17029)
-- Dependencies: 241
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.vehicles VALUES (1, 'TEST-100', 3, NULL, 7);


--
-- TOC entry 5268 (class 0 OID 0)
-- Dependencies: 244
-- Name: alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.alerts_id_seq', 1, true);


--
-- TOC entry 5269 (class 0 OID 0)
-- Dependencies: 226
-- Name: chat_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_history_id_seq', 1, false);


--
-- TOC entry 5270 (class 0 OID 0)
-- Dependencies: 232
-- Name: chat_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_messages_id_seq', 89, true);


--
-- TOC entry 5271 (class 0 OID 0)
-- Dependencies: 234
-- Name: conversation_states_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.conversation_states_id_seq', 14, true);


--
-- TOC entry 5272 (class 0 OID 0)
-- Dependencies: 246
-- Name: fleet_conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.fleet_conversations_id_seq', 1, false);


--
-- TOC entry 5273 (class 0 OID 0)
-- Dependencies: 222
-- Name: machines_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.machines_id_seq', 1, false);


--
-- TOC entry 5274 (class 0 OID 0)
-- Dependencies: 224
-- Name: problems_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.problems_id_seq', 2, true);


--
-- TOC entry 5275 (class 0 OID 0)
-- Dependencies: 230
-- Name: solutions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.solutions_id_seq', 3, true);


--
-- TOC entry 5276 (class 0 OID 0)
-- Dependencies: 228
-- Name: tickets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tickets_id_seq', 1, false);


--
-- TOC entry 5277 (class 0 OID 0)
-- Dependencies: 220
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 8, true);


--
-- TOC entry 5278 (class 0 OID 0)
-- Dependencies: 242
-- Name: vehicle_statuses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehicle_statuses_id_seq', 1, true);


--
-- TOC entry 5279 (class 0 OID 0)
-- Dependencies: 240
-- Name: vehicles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehicles_id_seq', 1, true);


--
-- TOC entry 5059 (class 2606 OID 17085)
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- TOC entry 5016 (class 2606 OID 16436)
-- Name: chat_history chat_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_pkey PRIMARY KEY (id);


--
-- TOC entry 5022 (class 2606 OID 16510)
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- TOC entry 5024 (class 2606 OID 16585)
-- Name: conversation_states conversation_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_states
    ADD CONSTRAINT conversation_states_pkey PRIMARY KEY (id);


--
-- TOC entry 5036 (class 2606 OID 16964)
-- Name: driver_workflows driver_workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.driver_workflows
    ADD CONSTRAINT driver_workflows_pkey PRIMARY KEY (id);


--
-- TOC entry 5062 (class 2606 OID 17104)
-- Name: fleet_conversations fleet_conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fleet_conversations
    ADD CONSTRAINT fleet_conversations_pkey PRIMARY KEY (id);


--
-- TOC entry 5010 (class 2606 OID 16408)
-- Name: machines machines_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machines
    ADD CONSTRAINT machines_pkey PRIMARY KEY (id);


--
-- TOC entry 5012 (class 2606 OID 16410)
-- Name: machines machines_serial_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machines
    ADD CONSTRAINT machines_serial_number_key UNIQUE (serial_number);


--
-- TOC entry 5034 (class 2606 OID 16933)
-- Name: owner_workflows owner_workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.owner_workflows
    ADD CONSTRAINT owner_workflows_pkey PRIMARY KEY (id);


--
-- TOC entry 5014 (class 2606 OID 16425)
-- Name: problems problems_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.problems
    ADD CONSTRAINT problems_pkey PRIMARY KEY (id);


--
-- TOC entry 5020 (class 2606 OID 16464)
-- Name: solutions solutions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.solutions
    ADD CONSTRAINT solutions_pkey PRIMARY KEY (id);


--
-- TOC entry 5018 (class 2606 OID 16449)
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (id);


--
-- TOC entry 5006 (class 2606 OID 16400)
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- TOC entry 5008 (class 2606 OID 16398)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 5047 (class 2606 OID 16984)
-- Name: vehicle_contacts vehicle_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_contacts
    ADD CONSTRAINT vehicle_contacts_pkey PRIMARY KEY (id);


--
-- TOC entry 5030 (class 2606 OID 16908)
-- Name: vehicle_monitoring vehicle_monitoring_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_monitoring
    ADD CONSTRAINT vehicle_monitoring_pkey PRIMARY KEY (id);


--
-- TOC entry 5055 (class 2606 OID 17065)
-- Name: vehicle_statuses vehicle_statuses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_statuses
    ADD CONSTRAINT vehicle_statuses_pkey PRIMARY KEY (id);


--
-- TOC entry 5057 (class 2606 OID 17067)
-- Name: vehicle_statuses vehicle_statuses_vehicle_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_statuses
    ADD CONSTRAINT vehicle_statuses_vehicle_id_key UNIQUE (vehicle_id);


--
-- TOC entry 5050 (class 2606 OID 17036)
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (id);


--
-- TOC entry 5052 (class 2606 OID 17038)
-- Name: vehicles vehicles_vehicle_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_vehicle_number_key UNIQUE (vehicle_number);


--
-- TOC entry 5060 (class 1259 OID 17091)
-- Name: ix_alerts_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_id ON public.alerts USING btree (id);


--
-- TOC entry 5025 (class 1259 OID 16528)
-- Name: ix_conversation_states_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_conversation_states_id ON public.conversation_states USING btree (legacy_id);


--
-- TOC entry 5026 (class 1259 OID 16527)
-- Name: ix_conversation_states_phone_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_conversation_states_phone_number ON public.conversation_states USING btree (phone_number);


--
-- TOC entry 5037 (class 1259 OID 16965)
-- Name: ix_driver_workflows_driver_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_driver_workflows_driver_phone ON public.driver_workflows USING btree (driver_phone);


--
-- TOC entry 5038 (class 1259 OID 16966)
-- Name: ix_driver_workflows_owner_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_driver_workflows_owner_phone ON public.driver_workflows USING btree (owner_phone);


--
-- TOC entry 5039 (class 1259 OID 16967)
-- Name: ix_driver_workflows_vehicle_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_driver_workflows_vehicle_number ON public.driver_workflows USING btree (vehicle_number);


--
-- TOC entry 5040 (class 1259 OID 16968)
-- Name: ix_driver_workflows_workflow_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_driver_workflows_workflow_status ON public.driver_workflows USING btree (workflow_status);


--
-- TOC entry 5063 (class 1259 OID 17110)
-- Name: ix_fleet_conversations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_fleet_conversations_id ON public.fleet_conversations USING btree (id);


--
-- TOC entry 5064 (class 1259 OID 17111)
-- Name: ix_fleet_conversations_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_fleet_conversations_phone ON public.fleet_conversations USING btree (phone);


--
-- TOC entry 5031 (class 1259 OID 16935)
-- Name: ix_owner_workflows_owner_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_owner_workflows_owner_phone ON public.owner_workflows USING btree (owner_phone);


--
-- TOC entry 5032 (class 1259 OID 16934)
-- Name: ix_owner_workflows_vehicle_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_owner_workflows_vehicle_number ON public.owner_workflows USING btree (vehicle_number);


--
-- TOC entry 5004 (class 1259 OID 16530)
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- TOC entry 5041 (class 1259 OID 16985)
-- Name: ix_vehicle_contacts_contact_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_contacts_contact_type ON public.vehicle_contacts USING btree (contact_type);


--
-- TOC entry 5042 (class 1259 OID 16986)
-- Name: ix_vehicle_contacts_driver_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_contacts_driver_phone ON public.vehicle_contacts USING btree (driver_phone);


--
-- TOC entry 5043 (class 1259 OID 16989)
-- Name: ix_vehicle_contacts_owner_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_contacts_owner_phone ON public.vehicle_contacts USING btree (owner_phone);


--
-- TOC entry 5044 (class 1259 OID 16988)
-- Name: ix_vehicle_contacts_vehicle_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_contacts_vehicle_number ON public.vehicle_contacts USING btree (vehicle_number);


--
-- TOC entry 5027 (class 1259 OID 16910)
-- Name: ix_vehicle_monitoring_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_monitoring_status ON public.vehicle_monitoring USING btree (status);


--
-- TOC entry 5028 (class 1259 OID 16909)
-- Name: ix_vehicle_monitoring_vehicle_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_monitoring_vehicle_number ON public.vehicle_monitoring USING btree (vehicle_number);


--
-- TOC entry 5053 (class 1259 OID 17073)
-- Name: ix_vehicle_statuses_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_statuses_id ON public.vehicle_statuses USING btree (id);


--
-- TOC entry 5048 (class 1259 OID 17054)
-- Name: ix_vehicles_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicles_id ON public.vehicles USING btree (id);


--
-- TOC entry 5045 (class 1259 OID 16987)
-- Name: ux_vehicle_contacts_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ux_vehicle_contacts_unique ON public.vehicle_contacts USING btree (vehicle_number, owner_phone, driver_phone, contact_type);


--
-- TOC entry 5073 (class 2606 OID 17086)
-- Name: alerts alerts_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id);


--
-- TOC entry 5066 (class 2606 OID 16437)
-- Name: chat_history chat_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 5074 (class 2606 OID 17105)
-- Name: fleet_conversations fleet_conversations_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fleet_conversations
    ADD CONSTRAINT fleet_conversations_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id);


--
-- TOC entry 5065 (class 2606 OID 16411)
-- Name: machines machines_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machines
    ADD CONSTRAINT machines_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- TOC entry 5068 (class 2606 OID 16465)
-- Name: solutions solutions_problem_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.solutions
    ADD CONSTRAINT solutions_problem_id_fkey FOREIGN KEY (problem_id) REFERENCES public.problems(id);


--
-- TOC entry 5067 (class 2606 OID 16450)
-- Name: tickets tickets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 5072 (class 2606 OID 17068)
-- Name: vehicle_statuses vehicle_statuses_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_statuses
    ADD CONSTRAINT vehicle_statuses_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id);


--
-- TOC entry 5069 (class 2606 OID 17049)
-- Name: vehicles vehicles_driver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_driver_id_fkey FOREIGN KEY (driver_id) REFERENCES public.users(id);


--
-- TOC entry 5070 (class 2606 OID 17039)
-- Name: vehicles vehicles_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.users(id);


--
-- TOC entry 5071 (class 2606 OID 17044)
-- Name: vehicles vehicles_supervisor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_supervisor_id_fkey FOREIGN KEY (supervisor_id) REFERENCES public.users(id);


-- Completed on 2026-06-03 11:31:23

--
-- PostgreSQL database dump complete
--

\unrestrict xzTqk5OdVApGrnTMkQc7vTHYZnLyFbv6tzYqv6UwePGv9foX95tDn39DPndDPAw


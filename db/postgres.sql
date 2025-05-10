-- DROP SCHEMA public;

CREATE ROLE semguser LOGIN PASSWORD 'your_password';

CREATE SCHEMA public AUTHORIZATION semguser;

COMMENT ON SCHEMA public IS 'standard public schema';

-- DROP SEQUENCE api_responses_id_seq;

CREATE SEQUENCE api_responses_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE api_responses_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE api_responses_id_seq TO semguser;

-- DROP SEQUENCE job_training_metadata_job_training_id_seq;

CREATE SEQUENCE job_training_metadata_job_training_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE job_training_metadata_job_training_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE job_training_metadata_job_training_id_seq TO semguser;

-- DROP SEQUENCE training_job_artifacts_job_id_seq;

CREATE SEQUENCE training_job_artifacts_job_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE training_job_artifacts_job_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE training_job_artifacts_job_id_seq TO semguser;

-- DROP SEQUENCE training_job_schedule_job_id_seq;

CREATE SEQUENCE training_job_schedule_job_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE training_job_schedule_job_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE training_job_schedule_job_id_seq TO semguser;

-- DROP SEQUENCE user_gesture_trainingmetadata_training_metadata_id_seq;

CREATE SEQUENCE user_gesture_trainingmetadata_training_metadata_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE user_gesture_trainingmetadata_training_metadata_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE user_gesture_trainingmetadata_training_metadata_id_seq TO semguser;

-- DROP SEQUENCE user_gestures_gestureid_seq;

CREATE SEQUENCE user_gestures_gestureid_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE user_gestures_gestureid_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE user_gestures_gestureid_seq TO semguser;

-- DROP SEQUENCE user_sensor_id_seq;

CREATE SEQUENCE user_sensor_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE user_sensor_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE user_sensor_id_seq TO semguser;

-- DROP SEQUENCE user_video_id_seq;

CREATE SEQUENCE user_video_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE user_video_id_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE user_video_id_seq TO semguser;

-- DROP SEQUENCE users_userid_seq;

CREATE SEQUENCE users_userid_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE users_userid_seq OWNER TO semguser;
GRANT ALL ON SEQUENCE users_userid_seq TO semguser;
-- public.user_gesture_trainingmetadata definition

-- Drop table

-- DROP TABLE user_gesture_trainingmetadata;

CREATE TABLE user_gesture_trainingmetadata (
	training_metadata_id serial4 NOT NULL,
	userid int4 NOT NULL,
	gestureid int4 NOT NULL,
	"timestamp" timestamptz NOT NULL,
	sample_number int4 NOT NULL,
	status varchar(50) NOT NULL,
	start_time timestamptz NOT NULL,
	end_time timestamptz NOT NULL,
	CONSTRAINT user_gesture_trainingmetadata_pkey PRIMARY KEY (training_metadata_id)
);

-- Permissions

ALTER TABLE user_gesture_trainingmetadata OWNER TO semguser;
GRANT ALL ON TABLE user_gesture_trainingmetadata TO semguser;


-- public.users definition

-- Drop table

-- DROP TABLE users;

CREATE TABLE users (
	userid serial4 NOT NULL,
	first_name varchar(100) NOT NULL,
	last_name varchar(100) NOT NULL,
	email varchar(150) NOT NULL,
	personal_description text NULL,
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (userid)
);

-- Permissions

ALTER TABLE users OWNER TO semguser;
GRANT ALL ON TABLE users TO semguser;


-- public.api_responses definition

-- Drop table

-- DROP TABLE api_responses;

CREATE TABLE api_responses (
	id serial4 NOT NULL,
	userid int4 NOT NULL,
	response text NOT NULL,
	"timestamp" timestamptz NOT NULL,
	CONSTRAINT api_responses_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user FOREIGN KEY (userid) REFERENCES users(userid)
);

-- Permissions

ALTER TABLE api_responses OWNER TO semguser;
GRANT ALL ON TABLE api_responses TO semguser;


-- public.training_job_schedule definition

-- Drop table

-- DROP TABLE training_job_schedule;

CREATE TABLE training_job_schedule (
	job_id serial4 NOT NULL,
	userid int4 NULL,
	actual_start_time timestamp NULL,
	actual_end_time timestamp NULL,
	job_status varchar(20) NULL,
	num_samples int4 NULL,
	error_message text NULL,
	log_messages varchar NULL,
	CONSTRAINT training_job_schedule_job_status_check CHECK (((job_status)::text = ANY (ARRAY[('scheduled'::character varying)::text, ('in-progress'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text, ('canceled'::character varying)::text]))),
	CONSTRAINT training_job_schedule_pkey PRIMARY KEY (job_id),
	CONSTRAINT fk_user FOREIGN KEY (userid) REFERENCES users(userid),
	CONSTRAINT training_job_schedule_userid_fkey FOREIGN KEY (userid) REFERENCES users(userid)
);

-- Permissions

ALTER TABLE training_job_schedule OWNER TO semguser;
GRANT ALL ON TABLE training_job_schedule TO semguser;


-- public.user_gestures definition

-- Drop table

-- DROP TABLE user_gestures;

CREATE TABLE user_gestures (
	gestureid serial4 NOT NULL,
	userid int4 NULL,
	gesture_description text NOT NULL,
	sensor_a0_used bool DEFAULT false NULL,
	sensor_a1_used bool DEFAULT false NULL,
	sensor_a2_used bool DEFAULT false NULL,
	sensor_a3_used bool DEFAULT false NULL,
	sensor_a4_used bool DEFAULT false NULL,
	sensor_a0_purpose text NULL,
	sensor_a1_purpose text NULL,
	sensor_a2_purpose text NULL,
	sensor_a3_purpose text NULL,
	sensor_a4_purpose text NULL,
	CONSTRAINT user_gestures_pkey PRIMARY KEY (gestureid),
	CONSTRAINT user_gestures_userid_fkey FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE
);

-- Permissions

ALTER TABLE user_gestures OWNER TO semguser;
GRANT ALL ON TABLE user_gestures TO semguser;


-- public.user_sensor definition

-- Drop table

-- DROP TABLE user_sensor;

CREATE TABLE user_sensor (
	id serial4 NOT NULL,
	userid int4 NULL,
	millis int4 NOT NULL,
	sensor_a0 float4 DEFAULT 0 NULL,
	sensor_a1 float4 DEFAULT 0 NULL,
	sensor_a2 float4 DEFAULT 0 NULL,
	sensor_a3 float4 DEFAULT 0 NULL,
	sensor_a4 float4 DEFAULT 0 NULL,
	ts timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT user_sensor_pkey PRIMARY KEY (id),
	CONSTRAINT user_sensor_userid_fkey FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE
);

-- Permissions

ALTER TABLE user_sensor OWNER TO semguser;
GRANT ALL ON TABLE user_sensor TO semguser;


-- public.user_video definition

-- Drop table

-- DROP TABLE user_video;

CREATE TABLE user_video (
	id serial4 NOT NULL,
	userid int4 NULL,
	video_frame bytea NOT NULL,
	"timestamp" timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT user_video_pkey PRIMARY KEY (id),
	CONSTRAINT user_video_userid_fkey FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE
);

-- Permissions

ALTER TABLE user_video OWNER TO semguser;
GRANT ALL ON TABLE user_video TO semguser;


-- public.job_training_metadata definition

-- Drop table

-- DROP TABLE job_training_metadata;

CREATE TABLE job_training_metadata (
	job_training_id serial4 NOT NULL,
	job_id int4 NULL,
	training_metadata_id int4 NULL,
	CONSTRAINT job_training_metadata_pkey PRIMARY KEY (job_training_id),
	CONSTRAINT job_training_metadata_job_id_fkey FOREIGN KEY (job_id) REFERENCES training_job_schedule(job_id)
);

-- Permissions

ALTER TABLE job_training_metadata OWNER TO semguser;
GRANT ALL ON TABLE job_training_metadata TO semguser;


-- public.training_job_artifacts definition

-- Drop table

-- DROP TABLE training_job_artifacts;

CREATE TABLE training_job_artifacts (
	job_id serial4 NOT NULL,
	userid int4 NOT NULL,
	model bytea NOT NULL,
	class_mapping jsonb NOT NULL,
	scaler bytea NOT NULL,
	sensors_used jsonb NOT NULL,
	CONSTRAINT training_job_artifacts_pkey PRIMARY KEY (job_id),
	CONSTRAINT training_job_artifacts_job_id_fkey FOREIGN KEY (job_id) REFERENCES training_job_schedule(job_id),
	CONSTRAINT training_job_artifacts_userid_fkey FOREIGN KEY (userid) REFERENCES users(userid)
);

-- Permissions

ALTER TABLE training_job_artifacts OWNER TO semguser;
GRANT ALL ON TABLE training_job_artifacts TO semguser;




-- Permissions

GRANT ALL ON SCHEMA public TO semguser;
GRANT ALL ON SCHEMA public TO public;


-- Table to store haptic mappings for gestures
CREATE TABLE gesture_haptic_mapping (
    mapping_id SERIAL PRIMARY KEY,
    gestureid INTEGER NOT NULL REFERENCES user_gestures(gestureid) ON DELETE CASCADE,
    userid INTEGER NOT NULL REFERENCES users(userid) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL, -- Order in the haptic sequence
    
    -- Motor activations (true/false for each finger motor)
    thumb_tip BOOLEAN NOT NULL DEFAULT false,
    thumb_base BOOLEAN NOT NULL DEFAULT false,
    index_tip BOOLEAN NOT NULL DEFAULT false,
    index_base BOOLEAN NOT NULL DEFAULT false,
    middle_tip BOOLEAN NOT NULL DEFAULT false,
    middle_base BOOLEAN NOT NULL DEFAULT false,
    ring_tip BOOLEAN NOT NULL DEFAULT false,
    ring_base BOOLEAN NOT NULL DEFAULT false,
    pinky_tip BOOLEAN NOT NULL DEFAULT false,
    pinky_base BOOLEAN NOT NULL DEFAULT false,
    
    -- Timestamps for audit and management
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint to ensure no more than 4 motors are active at once
    CONSTRAINT max_four_motors CHECK (
        (CASE WHEN thumb_tip THEN 1 ELSE 0 END) +
        (CASE WHEN thumb_base THEN 1 ELSE 0 END) +
        (CASE WHEN index_tip THEN 1 ELSE 0 END) +
        (CASE WHEN index_base THEN 1 ELSE 0 END) +
        (CASE WHEN middle_tip THEN 1 ELSE 0 END) +
        (CASE WHEN middle_base THEN 1 ELSE 0 END) +
        (CASE WHEN ring_tip THEN 1 ELSE 0 END) +
        (CASE WHEN ring_base THEN 1 ELSE 0 END) +
        (CASE WHEN pinky_tip THEN 1 ELSE 0 END) +
        (CASE WHEN pinky_base THEN 1 ELSE 0 END) <= 4
    )
);

-- Index for faster lookups
CREATE INDEX idx_gesture_haptic_mapping_gesture_id ON gesture_haptic_mapping(gestureid);
CREATE INDEX idx_gesture_haptic_mapping_user_id ON gesture_haptic_mapping(userid);

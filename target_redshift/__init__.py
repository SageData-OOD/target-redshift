import psycopg2
import singer
from singer import utils
from target_postgres import target_tools
from target_postgres.postgres import MillisLoggingConnection

from target_redshift.redshift import RedshiftTarget
from target_redshift.s3 import S3

LOGGER = singer.get_logger()

REQUIRED_CONFIG_KEYS = [
    'redshift_host',
    'redshift_database',
    'redshift_username',
    'redshift_password',
    'target_s3'
]


def main(config, input_stream=None):
    with psycopg2.connect(
            connection_factory=MillisLoggingConnection,
            host=config.get('redshift_host'),
            port=config.get('redshift_port', 5439),
            dbname=config.get('redshift_database'),
            user=config.get('redshift_username'),
            password=config.get('redshift_password')
    ) as connection:
        s3_config = config.get('target_s3')
        s3 = S3(s3_config.get('aws_access_key_id'),
                s3_config.get('aws_secret_access_key'),
                s3_config.get('bucket'),
                s3_config.get('key_prefix'),
                aws_session_token=s3_config.get('aws_session_token'))

        redshift_target = RedshiftTarget(
            connection,
            s3,
            redshift_schema=config.get('redshift_schema', 'public'),
            logging_level=config.get('logging_level'),
            default_column_length=config.get('default_column_length', 1000),
            persist_empty_tables=config.get('persist_empty_tables'),
            # TODO: DP fix
            redshift_copy_options=config.get('redshift_copy_options')
        )

        # TODO: DP
        with redshift_target.conn.cursor() as cur:
            create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {config.get('redshift_schema', 'public')}"
            # print(create_schema_sql)
            cur.execute(create_schema_sql)

        if input_stream:
            target_tools.stream_to_target(input_stream, redshift_target, config=config)
        else:
            target_tools.main(redshift_target)


def cli():
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)
    main(args.config)

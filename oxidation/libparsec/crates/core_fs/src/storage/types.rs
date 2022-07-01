// Parsec Cloud (https://parsec.cloud) Copyright (c) BSLv1.1 (eventually AGPLv3) 2016-2021 Scille SAS

use diesel::{
    deserialize::FromSql,
    serialize::{Output, ToSql},
    sqlite::{Sqlite, SqliteValue},
    AsExpression, FromSqlRow,
};

#[derive(Debug, AsExpression, FromSqlRow)]
#[diesel(sql_type = diesel::sql_types::Double)]
pub struct DateTime(pub f64);

impl ToSql<diesel::sql_types::Double, Sqlite> for DateTime
where
    f64: ToSql<diesel::sql_types::Double, Sqlite>,
{
    fn to_sql<'b>(&'b self, out: &mut Output<'b, '_, Sqlite>) -> diesel::serialize::Result {
        <f64 as ToSql<diesel::sql_types::Double, Sqlite>>::to_sql(&self.0, out)
    }
}

impl FromSql<diesel::sql_types::Double, Sqlite> for DateTime
where
    f64: FromSql<diesel::sql_types::Double, Sqlite>,
{
    fn from_sql(bytes: SqliteValue) -> diesel::deserialize::Result<Self> {
        <f64 as FromSql<diesel::sql_types::Double, Sqlite>>::from_sql(bytes).map(Self)
    }
}

impl From<parsec_api_types::DateTime> for DateTime {
    fn from(dt: parsec_api_types::DateTime) -> Self {
        Self(dt.get_f64_with_us_precision())
    }
}

impl From<DateTime> for parsec_api_types::DateTime {
    fn from(dt: DateTime) -> Self {
        Self::from_f64_with_us_precision(dt.0)
    }
}
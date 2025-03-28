use actix_files::{NamedFile, Files};
use actix_web::{get, App, HttpServer, Responder, HttpResponse};
use config::{Config, FileFormat, ConfigError};
use log::info;
use clap::{Command, Arg};
use std::path::{Path, PathBuf};
use tokio::signal;
use thiserror::Error;

mod interface_manager;
use interface_manager::InterfaceManager;

const DEFAULT_CONFIG: &str = "network-configuration.default.conf";

struct WEBParameters {
    start_server: bool,
    port: u16,
    address: String,
    ap_hide_in_ui: bool,
    ap_interface: String,
    reverse_proxy_path: String,
}

#[derive(Error, Debug)]
pub enum ParametersInitError {
    #[error("Configuration error: {0}")]
    Config(#[from] ConfigError),
    #[error("Unknown parameters initialisation error")]
    Unknown,
}

impl WEBParameters {
    fn new(def_config: &Config)-> Result<Self, ParametersInitError> {
        let start_server: bool = def_config.get("Server.EnableServer")?;
        let port: u16 = def_config.get("Server.Port")?;
        let address: String = def_config.get("Server.Address")?;
        let ap_hide_in_ui: bool = def_config.get("AP.APHideInUI")?;
        let ap_interface: String = def_config.get("AP.APInterfaceDevice")?;
        let reverse_proxy_path: String = def_config.get("Server.ReverseProxyPath")?;
        Ok(Self {
            start_server,
            port,
            address,
            ap_hide_in_ui,
            ap_interface,
            reverse_proxy_path,
        })
    }
}

#[get("/")]
async fn index() -> impl Responder {
    let path: PathBuf = Path::new("static").join("index.html");
    NamedFile::open(path).map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("File not found: {}", e))
    })
}

async fn get_status() -> impl Responder {
    // return jsonify(self.manager.get_status())
    HttpResponse::Ok()
}

// async fn get_config(&self) -> impl Responder {
//     let config = self.manager.get_conf()?;
//     HttpResponse::Ok().json(&config);
// }

// async fn post_config(&self, config: web::Json<serde_json::Value>) -> impl Responder {
//     self.manager.load_config(config).await;
//     HttpResponse::Ok();
// }

#[allow(unused_variables)]
async fn run(parameters:&WEBParameters, manager: &InterfaceManager) -> std::io::Result<()> {
    if parameters.start_server {
        let server_string = format!("{}{}", parameters.address, parameters.port);
        // info!(format!("Starting server on http://{}", server_string));

        HttpServer::new(move || {
            // let service_clone = Arc::clone(&service);
            App::new()
                // .app_data(manager.clone())
                .service(Files::new("/static", "static").prefer_utf8(true))
                .service(index)
                // .route("/api/status", web::get().to(NetworkConfigurationService::get_status))
                // .route("/api/config", web::get().to(NetworkConfigurationService::get_config))
                // .route("/api/config", web::post().to(NetworkConfigurationService::post_config))
            // .route("/api/interfaces", web::get().to(get_interfaces))
            // .route("/api/{interface_id}/config", web::get().to(interface_config))
        })
            .bind(server_string)?
            .run()
            .await
    }else{
        info!("Waiting indefinitely...");
        signal::ctrl_c().await?;
        info!("Received Ctrl+C, exiting...");
        Ok(())
    }
}

//noinspection HttpUrlsUsage
#[actix_web::main]
async fn main() -> std::io::Result<()> {

    let matches = Command::new(clap::crate_name!())
        .author(clap::crate_authors!())
        .about(clap::crate_description!())
        .version(clap::crate_version!())
        .arg(
            Arg::new("conf")
                .short('c')
                .long("config")
                .required(true)
                .help("Configuration file"),
        )
        .get_matches();

    let config_file = matches
        .get_one::<String>("config")
        .expect("Configuration file is required");

    let def_config = Config::builder()
        .add_source(config::File::new(DEFAULT_CONFIG, FileFormat::Ini))
        .add_source(config::File::new(config_file, FileFormat::Ini).required(false))
        .build()
        .expect("Failed to read configuration.");

    let web_parameters = WEBParameters::new(&def_config).expect("Failed to load configuration");
    let manager = InterfaceManager::new(&def_config)?;
    run(&web_parameters, &manager).await?;

    Ok(())
}

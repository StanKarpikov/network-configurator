use std::any::Any;
use actix_files::{NamedFile, Files};
use actix_web::{web, App, HttpServer, HttpRequest, Responder, HttpResponse, Error, Result};
use std::sync::{Arc, Mutex};
use config::{Config, File, FileFormat, ConfigError};
use log::{info, error};
use clap::{Command, Arg};
use std::path::{PathBuf, Path};
use tokio::signal;

mod interface_manager;
use interface_manager::InterfaceManager;

const DEFAULT_CONFIG: &str = "network-configuration.default.conf";

struct NetworkConfigurationService {
    start_server: bool,
    port: i16,
    address: String,
    ap_hide_in_ui: bool,
    ap_interface: String,
    reverse_proxy_path: String,
    manager: InterfaceManager,
}

impl NetworkConfigurationService {

    fn new(def_config: &Config)-> Result<Self, ConfigError> {
        let start_server: bool = def_config.get("Server.EnableServer")?;
        let port: i16 = def_config.get("Server.Port")?;
        let address: String = def_config.get("Server.Address")?;
        let ap_hide_in_ui: bool = def_config.get("AP.APHideInUI")?;
        let ap_interface: String = def_config.get("AP.APInterfaceDevice")?;
        let reverse_proxy_path: String = def_config.get("Server.ReverseProxyPath")?;
        let manager = InterfaceManager::new(def_config)?;
        Ok(Self {
            start_server,
            port,
            address,
            ap_hide_in_ui,
            ap_interface,
            reverse_proxy_path,
            manager,
        })
    }

    async fn index(&self, req: HttpRequest) -> Result<NamedFile> {
        if let Some(filename) = req.match_info().get("filename") {
            let path: PathBuf = Path::new("static").join(filename);
            // Handle the possibility of file not being found or other errors
            NamedFile::open(path).map_err(|e| {
                actix_web::error::ErrorInternalServerError(format!("File not found: {}", e))
            })
        } else {
            Err(actix_web::error::ErrorBadRequest("Filename parameter is missing"))
        }
    }

    async fn get_status(&self) -> impl Responder {
        // return jsonify(self.manager.get_status())
        HttpResponse::Ok()
    }

    async fn get_config(&self) -> impl Responder {
        let config = self.manager.get_conf()?;
        HttpResponse::Ok().json(&config);
    }

    async fn post_config(&self, config: web::Json<serde_json::Value>) -> impl Responder {
        self.manager.load_config(config).await;
        HttpResponse::Ok();
    }

    async fn run(&self) -> std::io::Result<()> {
        if self.start_server {
            let server_string = format!("{}{}", self.address, self.port);
            info!(format!("Starting server on http://{server_string}"));

            HttpServer::new(move || {
                App::new()
                    .service(Files::new("/static", "static").prefer_utf8(true))
                    .route("/", web::get().to(NetworkConfigurationService::index))
                    .route("/api/status", web::get().to(NetworkConfigurationService::get_status))
                    .route("/api/config", web::get().to(NetworkConfigurationService::get_config))
                    .route("/api/config", web::post().to(NetworkConfigurationService::post_config))
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

    Arc::new(NetworkConfigurationService::new(&def_config).unwrap().run().await);

    Ok(())
}

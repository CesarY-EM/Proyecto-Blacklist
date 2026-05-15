package mx.com.telmex.reduno.aplicaciones.blacklistCheck.controller;


import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.List;
 
import javax.servlet.http.HttpServletResponse;
 
import org.apache.commons.lang.exception.ExceptionUtils;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.bson.Document;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
 
import com.fasterxml.jackson.databind.ObjectMapper;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
 
import lombok.extern.log4j.Log4j;
import mx.com.telmex.reduno.aplicaciones.blacklistCheck.vo.ExecScriptVo;
import mx.com.telmex.reduno.aplicaciones.blacklistCheck.vo.ListaSubredesVo;
import mx.com.telmex.reduno.dao.generic.IGenericDAO;
import mx.com.telmex.reduno.utilidades.constantes.ApplicationConstants;
import mx.com.telmex.reduno.utilidades.enviorest.IEnvioPeticionRestFulService;
@Log4j
@RestController
public class blacklistCheckController {

    @Autowired
    private IEnvioPeticionRestFulService envioPeticionRestFulService;

    @Autowired
    private IGenericDAO genericDAO;

     @PostMapping("/blacklistCheck")
    public String blacklistCheckList(
            @RequestBody ListaSubredesVo listaSubredes,
            HttpServletResponse httpServletResponse) throws IOException {

        StringBuilder logStringBuilder;

        if (log.isDebugEnabled()) {
            logStringBuilder = new StringBuilder();
            logStringBuilder.append(ApplicationConstants.SALTO_LINEA);
            logStringBuilder.append(ApplicationConstants.LOG_INICIO);
            logStringBuilder.append(Thread.currentThread().getStackTrace()[1].getMethodName());
            log.debug(logStringBuilder.toString());
        }

        String request = "";

        try {
            log.debug("Inicia blacklistCheck");

            List<String> listaEx = listaSubredes.getListaSubredes();
            log.info("Subred recibida: " + listaEx.get(0));

            ExecScriptVo execScriptVo = new ExecScriptVo();
            execScriptVo.setArgs(listaEx);
            execScriptVo.setDirScript("/home/ngsop/lilaApp/plugins/scripts/blacklist_check/main.py");

            ObjectMapper objectMapper = new ObjectMapper();
            String path = objectMapper.writeValueAsString(execScriptVo);

            log.info("Datos enviados a LILA");
            log.info(path);

            request = envioPeticionRestFulService.enviarPeticion(
                    "https://201.154.139.4:8081/execScriptWithArgs",
                    null,
                    path,
                    HttpMethod.POST);

            log.debug("Respuesta de LILA: " + request);

        } catch (Exception ex) {

            logStringBuilder = new StringBuilder();
            logStringBuilder.append(ApplicationConstants.SALTO_LINEA);
            logStringBuilder.append(ApplicationConstants.LOG_ERROR);
            logStringBuilder.append(Thread.currentThread().getStackTrace()[1].getMethodName());
            logStringBuilder.append(ApplicationConstants.SALTO_LINEA);
            logStringBuilder.append(ExceptionUtils.getStackTrace(ex));

            log.error(logStringBuilder.toString());

            httpServletResponse.sendError(
                    HttpServletResponse.SC_BAD_REQUEST,
                    ex.getMessage());
        }

        return request;
    }

@PostMapping("/downloadExcel")
public ResponseEntity<Resource> downloadExcel() {

    MongoClient mongoClient = null;

    try {

        mongoClient = MongoClients.create("mongodb://localhost:27017"); //mongodb://admin:gsoppower@201.154.139.4:8445
        MongoDatabase database = mongoClient.getDatabase("blacklistDB");
        MongoCollection<Document> collection = database.getCollection("reportes");

        Document documento = collection.find().first();

        if (documento == null) {
            log.error("No se encontró ningún reporte en MongoDB");
            return ResponseEntity.notFound().build();
        }

        Workbook workbook = new XSSFWorkbook();

        Sheet sheetBloqueo   = workbook.createSheet("BLOQUEO");
        Sheet sheetLimpio    = workbook.createSheet("LIMPIO");
        Sheet sheetAuditoria = workbook.createSheet("AUDITORIA");


        Row headerBloqueo = sheetBloqueo.createRow(0);
        headerBloqueo.createCell(0).setCellValue("Bloque");
        headerBloqueo.createCell(1).setCellValue("Resultado");

        Row headerLimpio = sheetLimpio.createRow(0);
        headerLimpio.createCell(0).setCellValue("Bloque");
        headerLimpio.createCell(1).setCellValue("Resultado");

        Row headerAuditoria = sheetAuditoria.createRow(0);
        headerAuditoria.createCell(0).setCellValue("Bloque");
        headerAuditoria.createCell(1).setCellValue("IP");
        headerAuditoria.createCell(2).setCellValue("Dominios");
        headerAuditoria.createCell(3).setCellValue("Resultado");


        int rowBloqueo   = 1;
        int rowLimpio    = 1;
        int rowAuditoria = 1;

        Document bloquesPrincipales = (Document) documento.get("bloques");

        for (String bloqueOriginal : bloquesPrincipales.keySet()) {

            Document datosBloqueOriginal = (Document) bloquesPrincipales.get(bloqueOriginal);
            Document subBloques = (Document) datosBloqueOriginal.get("bloques");

            for (String subBloque : subBloques.keySet()) {

                Document datosSubBloque = (Document) subBloques.get(subBloque);
                String resultado = datosSubBloque.getString("resultado");
                List<Document> ips = (List<Document>) datosSubBloque.get("ips");

                if ("BLOQUEO".equals(resultado)) {

                    Row row = sheetBloqueo.createRow(rowBloqueo++);
                    row.createCell(0).setCellValue(subBloque);
                    row.createCell(1).setCellValue(resultado);

                } else if ("LIMPIO".equals(resultado)) {

                    Row row = sheetLimpio.createRow(rowLimpio++);
                    row.createCell(0).setCellValue(subBloque);
                    row.createCell(1).setCellValue(resultado);

                } else if ("AUDITORIA".equals(resultado)) {

                    if (ips != null && !ips.isEmpty()) {
                        for (Document ipData : ips) {
                            Row row = sheetAuditoria.createRow(rowAuditoria++);
                            row.createCell(0).setCellValue(subBloque);
                            row.createCell(1).setCellValue(ipData.getString("ip"));
                            row.createCell(2).setCellValue(ipData.getString("dominios"));
                            row.createCell(3).setCellValue(resultado);
                        }
                    } else {
                        Row row = sheetAuditoria.createRow(rowAuditoria++);
                        row.createCell(0).setCellValue(subBloque);
                        row.createCell(1).setCellValue("-");
                        row.createCell(2).setCellValue("-");
                        row.createCell(3).setCellValue(resultado);
                    }
                }
            }
        }


        for (int i = 0; i < 2; i++) sheetBloqueo.autoSizeColumn(i);
        for (int i = 0; i < 2; i++) sheetLimpio.autoSizeColumn(i);
        for (int i = 0; i < 4; i++) sheetAuditoria.autoSizeColumn(i);


        ByteArrayOutputStream out = new ByteArrayOutputStream();
        workbook.write(out);
        workbook.close();

        ByteArrayResource resource = new ByteArrayResource(out.toByteArray());

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=reporte.xlsx")
                .contentType(MediaType.parseMediaType(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                .contentLength(resource.contentLength())
                .body(resource);

    } catch (Exception ex) {
        log.error("Error generando Excel: ", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();

    } finally {
        if (mongoClient != null) {
            mongoClient.close();
        }
    }
}
}

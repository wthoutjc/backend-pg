class EstructurasHTML():
    def __init__(self):
        self.ESTRUCTURA_UPDATE_PASSWORD = None

    def get_estructura_html_update_password(self, nombre, apellido, code, linkJWT):
        '''
        Estructura HTML para actualización de contraseña.
        '''
        self.ESTRUCTURA_UPDATE_PASSWORD = f"""
            <div style="padding: 0px; margin: 0px auto; font-family: 'Montserrat', sans-serif; width: 100% !important;">
                <div style="overflow:hidden; color:transparent; visibility:hidden; width:0; font-size:0; opacity:0; height:0">
                    Por favor, confirma que eres tú.
                </div>
                <table role="presentation" align="center" border="0" cellspacing="0" cellpadding="0" width="100%"
                    bgcolor="#EDF0F3" style="background-color:#079992; table-layout:fixed">
                    <tbody>
                        <tr>
                            <td align="center" style="">
                                <center style="width:100%; background: url('https://i.postimg.cc/qR1wSbqc/background.jpg');">
                                    <table role="presentation" border="0" class="x_phoenix-email-container" cellspacing="0"
                                        cellpadding="0" width="512" bgcolor="#FFFFFF"
                                        style="background-color: #079992; margin:0 auto; max-width:512px; width:inherit">
                                        <tbody>
                                            <tr>
                                                <td bgcolor="#F6F8FA"
                                                    style="background-color:#04706b; padding:12px; border-bottom:1px solid #ECECEC">
                                                    <table role="presentation" border="0" cellspacing="0" cellpadding="0"
                                                        width="100%" style="width:100%!important; min-width:100%!important">
                                                        <tbody>
                                                            <tr>
                                                                <td align="left" valign="middle" style="">
                                                                    <a href="http://produgan-frontend-bucket.s3-website-sa-east-1.amazonaws.com/"
                                                                        target="_blank" rel="noopener noreferrer"
                                                                        data-auth="NotApplicable"
                                                                        style="color:#0073B1; display:inline-block; text-decoration:none"
                                                                        data-linkindex="0">
                                                                        <img data-imagetype="External"
                                                                            src="https://i.postimg.cc/mr87gc4B/produgan-white.png"
                                                                            alt="Produgan S.A.S" border="0" height="44" width="140"
                                                                            style="outline:none; color:#FFFFFF; text-decoration:none">
                                                                    </a>
                                                                </td>
                                                                <td width="1" style="">
                                                                    &nbsp;
                                                                </td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="">
                                                    <table role="presentation" border="0" cellspacing="0" cellpadding="0"
                                                        width="100%" style="">
                                                        <tbody>
                                                            <tr>
                                                                <td style="padding:20px 24px 10px 24px">
                                                                    <table role="presentation" border="0" cellspacing="0"
                                                                        cellpadding="0" width="100%" style="">
                                                                        <tbody>
                                                                            <tr>
                                                                                <td style="padding-bottom:20px">
                                                                                    <h2
                                                                                        style="margin:0; color:#FFF; font-weight:700; font-size:20px; line-height:1.2">
                                                                                        Hola, {nombre} {apellido}:
                                                                                    </h2>
                                                                                </td>
                                                                            </tr>
                                                                            <tr>
                                                                                <td style="padding-bottom:20px">
                                                                                    <p
                                                                                        style="margin:0; color:#FFF; font-weight:400; font-size:16px; line-height:1.25">
                                                                                        Se esta procesando una solicitud de cambio de contraseña. Para actualizar su información de seguridad haga clic en el botón de abajo E INGRESE SU CÓDIGO DE REACTIVACIÓN
                                                                                    </p>
                                                                                    <p
                                                                                        style="margin:0; color:#FFF; font-weight:400; font-size:16px; line-height:1.25">
                                                                                        CÓDIGO: {code}
                                                                                    </p>
                                                                                </td>
                                                                            </tr>
                                                                        </tbody>
                                                                    </table>
                                                                </td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td align="center" style="padding:0 0 8px 0; text-align:center">
                                                    <a href={linkJWT}
                                                        target="_blank" rel="noopener noreferrer" data-auth="NotApplicable"
                                                        style="color:#6A6C6D; text-decoration:underline; display:inline-block"
                                                        data-linkindex="4">
                                                        <button style="background-color: #112233; color: white;font-family: 'Montserrat', sans-serif;font-weight:200;padding:10px;"> CAMBIAR CONTRASEÑA </button>
                                                    </a>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </center>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """
        return self.ESTRUCTURA_UPDATE_PASSWORD
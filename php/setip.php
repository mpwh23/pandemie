<?php

define("DB_HOST", "db5000350590.hosting-data.io");
define("DB_USER", "dbu86934");
define("DB_PASSWORD", "Q&xw+C#52!Frda9g8");
define("DB_DATABASE", "dbs340708");


if (isset($_GET['ip'])) {
	
	$con = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD,DB_DATABASE);
	
	$cmd = "UPDATE python SET id=1, ip='" . $_GET['ip'] . "', port=" . $_GET['port'];
	$res = mysqli_query($con, $cmd);
		
	mysqli_close($con);
	echo "done";
	
}else{
	echo "fail";
}

?>
	
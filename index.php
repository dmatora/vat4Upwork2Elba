<?php
function getValue($xml) {
    $cbr = simplexml_load_string($xml);
    foreach ($cbr->Valute as $valute) {
        if ($valute->CharCode == 'USD') {
            break;
        }
    }
    return (float) str_replace(',', '.', $valute->Value);
}

function getFromCache($url, $code) {
    mkdir('.db');
    $filename = '.db/' . $code;
    if (file_exists($filename)) {
        return file_get_contents($filename);
    }
    $xml = file_get_contents($url);
    file_put_contents($filename, $xml);
    return $xml;
}

    if ($_REQUEST['csv']) {
        $data = explode("\n", $_REQUEST['csv']);
        ?>
        <style>td {padding: 0 10px 0 10px }</style>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
        <table><?php
        foreach ($data as $string) {
            if (empty($string)) continue;
            $array = str_getcsv($string);
            unset($array[4]);
            unset($array[5]);
            unset($array[6]);
            unset($array[7]);
            unset($array[8]);
            $date = $array[0];
            if ($date == 'Date') {
                $array[10] = 'Курс';
                $array[11] = 'Дата';
                $array[12] = 'Цена за ед.';
                $array[13] = 'Всего, с учетом НДС';
                $array[14] = 'НДС';
                echo '<tr><td>'.implode('</td><td>',$array).'</td></tr>';
                continue;
            }
            $type = $array[2];
            if (in_array($type, ['Withdrawal Fee', 'Withdrawal'])) {
                continue;
            }
            $dateReq = date('d/m/Y', strtotime($date));
            $code = date('Y-m-d', strtotime($date));
            $dateElba = date('d.m.Y', strtotime($date));
            $xml = getFromCache('http://www.cbr.ru/scripts/XML_daily_eng.asp?date_req='.$dateReq, $code);

            $cbr = getValue($xml);
            $roubles = round(-$array[9] * $cbr, 2);
            $nds = round($roubles * 0.18, 2);
            $roublesWithNds = $roubles + $nds;

            $array[9] = '$'.substr($array[9], 1);
            $array[10] = $cbr;
            $array[11] = $dateElba;
            $array[12] = $roubles;
            $array[13] = $roublesWithNds;
            $array[14] = $nds;
            $array[15] = '<button onclick="$(this).parent().parent().hide()">Скрыть</button>';
            $ndsTotal += $nds;
            $ndsTotalString .= '+'.$nds;
            echo '<tr><td>'.implode('</td><td>',$array).'</td></tr>';
        }
            $ndsTotalString = substr($ndsTotalString, 1);
        ?></table>
        <h3>Итого НДС: <?php echo $ndsTotalString.'='.$ndsTotal ?></h3>
        <?php
        exit;
    }
?>
<form method="POST" style="text-align:center;width:80%;margin: 0 auto">
    <p><textarea name="csv" style="width:100%;height:400px"></textarea></p>
    <input type="submit">
</form>